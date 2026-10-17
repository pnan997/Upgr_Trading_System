#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
walk_forward.py
===============

Orchestrateur de walk-forward : enchaine, section par section, les 3 programmes
existants (predictions, enrichissement OHLCV, backtest) sur des decoupes
glissants du dataset de features.

- Etape 0 : cache des features (compute_all du programme 1, calcule une seule
  fois sur toute la base) dans wf_features_full.csv.
- Grille : decoupage en JOURS DE BOURSE (dates distinctes des features) :
  train de train_jours, gap de gap_jours, test de test_jours, avance de
  pas_jours a chaque section.
- Reprise : une section deja terminee (knn_backtest.summary.csv present) est
  skippee.
- Sorties : walk_forward_resume.csv et walk_forward_resume.md dans l'atelier.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
ATDIR        = Path(__file__).parent
BASE         = Path(os.environ["TS_ROOT"]) / "Features_Pente_Walk_Forward"
SECTIONS_DIR = ATDIR / "wf_sections"
CACHE        = ATDIR / "wf_features_full.csv"
RESUME_CSV   = ATDIR / "walk_forward_resume.csv"
RESUME_MD    = ATDIR / "walk_forward_resume.md"

CONFIG_PATH = ATDIR / "walk_forward_config.json"

# Colonnes du CSV de resume
RESUME_COLS = ["section", "train_debut", "train_fin", "test_debut", "test_fin",
               "n_trades", "pnl_brut", "pnl_net", "retour_pct", "win_rate_pct",
               "max_drawdown", "frais", "slippage"]


# ---------------------------------------------------------------------------
# Etape 0 : cache des features
# ---------------------------------------------------------------------------
def build_features_cache() -> pd.DataFrame:
    """Calcule les features sur toute la base (replication de main() du
    programme 1, SANS le split quantile) et les sauvegarde en cache."""
    # Import de compute_all depuis generate_training_dataset.py (meme dossier)
    sys.path.insert(0, str(ATDIR))
    from generate_training_dataset import compute_all

    db_path = os.environ["TS_DB_PATH"]
    conn = duckdb.connect(db_path, read_only=True)
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'ohlcv_%'"
    ).fetchall()
    tickers = [t[0].replace('ohlcv_', '') for t in tables]

    all_dfs = []
    for i, symbol in enumerate(tickers, start=1):
        try:
            table_name = f'ohlcv_{symbol}'
            df = conn.execute(f'SELECT * FROM "{table_name}" ORDER BY date ASC').df()
            if df.empty or len(df) < 71:  # au moins 60 jours de features + 10 de target
                continue
            df.columns = [c.lower() for c in df.columns]
            all_dfs.append(compute_all(symbol, df))
        except Exception as e:
            print(f"Erreur sur {symbol} : {e}")
        if i % 300 == 0:
            print(f"  ... {i}/{len(tickers)} symboles traites")
    conn.close()

    if not all_dfs:
        raise RuntimeError("Aucune donnee : cache des features impossible.")

    full_df = pd.concat(all_dfs, ignore_index=True)
    full_df['date'] = pd.to_datetime(full_df['date'])
    full_df.to_csv(CACHE, index=False)
    print(f"Cache des features sauvegarde : {CACHE} ({len(full_df)} lignes)")
    return full_df


def load_features() -> pd.DataFrame:
    """Charge le cache des features (le recalcule s'il n'existe pas)."""
    if CACHE.exists():
        print(f"Cache des features deja present : {CACHE}")
        return pd.read_csv(CACHE, parse_dates=["date"])
    print("Pas de cache : calcul des features sur toute la base...")
    return build_features_cache()


# ---------------------------------------------------------------------------
# Grille des sections
# ---------------------------------------------------------------------------
def build_sections(dates, cfg):
    """Construit la grille walk-forward sur les dates distinctes des features.
    dates doit etre une liste triee. Arret quand test est vide.
    Retour : liste de dicts {nom, train (2 dates), test (2 dates)}."""
    train_jours = cfg["train_jours"]
    gap_jours   = cfg["gap_jours"]
    test_jours  = cfg["test_jours"]
    pas_jours   = cfg["pas_jours"]

    sections = []
    k = 0
    while True:
        train_start_idx = k * pas_jours
        train = dates[train_start_idx: train_start_idx + train_jours]
        test_start_idx = train_start_idx + train_jours + gap_jours
        test = dates[test_start_idx: test_start_idx + test_jours]
        if len(test) == 0:
            break
        nom = f"section{k + 1:02d}_{test[0]:%Y%m%d}_{test[-1]:%Y%m%d}"
        sections.append({
            "nom": nom,
            "train_debut": train[0], "train_fin": train[-1],
            "test_debut": test[0],   "test_fin": test[-1],
        })
        k += 1
    return sections


# ---------------------------------------------------------------------------
# Lancement des programmes 2, 3 et 4
# ---------------------------------------------------------------------------
def run_program(script_path: Path, log_path: Path, env_vars: dict) -> bool:
    """Lance un programme en sous-processus avec variables d'env ajoutees,
    sortie redirigee vers log_path. Retourne True si returncode == 0."""
    env = {**os.environ, **env_vars}
    with open(log_path, "w", encoding="utf-8") as logf:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            env=env, stdout=logf, stderr=subprocess.STDOUT,
        )
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------
def load_existing_sections(resume_path: Path) -> set:
    """Noms de sections deja presents dans le CSV de resume (anti-doublons)."""
    if not resume_path.exists():
        return set()
    try:
        df = pd.read_csv(resume_path)
        return set(df["section"].astype(str))
    except Exception:
        return set()


def append_resume_row(row: dict) -> None:
    """Ajoute une ligne au CSV de resume (cree avec en-tete si absent)."""
    write_header = not RESUME_CSV.exists()
    df = pd.DataFrame([row], columns=RESUME_COLS)
    df.to_csv(RESUME_CSV, mode="a", header=write_header, index=False)


def build_resume_row(sec, summary_path: Path) -> dict:
    """Construit la ligne de resume d'une section a partir du summary.csv du
    backtest, ou une ligne ERREUR si le summary est absent/illisible."""
    row = {
        "section": sec["nom"],
        "train_debut": f"{sec['train_debut']:%Y-%m-%d}",
        "train_fin":   f"{sec['train_fin']:%Y-%m-%d}",
        "test_debut":  f"{sec['test_debut']:%Y-%m-%d}",
        "test_fin":    f"{sec['test_fin']:%Y-%m-%d}",
        "n_trades": "", "pnl_brut": "", "pnl_net": "", "retour_pct": "",
        "win_rate_pct": "", "max_drawdown": "", "frais": "", "slippage": "",
    }
    try:
        s = pd.read_csv(summary_path).iloc[0]
        row.update({
            "n_trades":     round(float(s["n_trades"]), 2),
            "pnl_brut":     round(float(s["pnl_brut_total"]), 2),
            "pnl_net":      round(float(s["pnl_net_total"]), 2),
            "retour_pct":   round(float(s["retour_pct"]), 2),
            "win_rate_pct": round(float(s["win_rate_pct"]), 2),
            "max_drawdown": round(float(s["max_drawdown_cumul_eur"]), 2),
            "frais":        round(float(s["total_frais"]), 2),
            "slippage":     round(float(s["total_slippage"]), 2),
        })
    except Exception:
        row["n_trades"] = "ERREUR"
    return row


# ---------------------------------------------------------------------------
# Resume markdown
# ---------------------------------------------------------------------------
NOTE_IMPLEM = """\
Note — choix d'implementation (pas d'interpretation des resultats) :
- Features calculees une seule fois (fonction compute_all du programme 1), puis
  decoupees par section — les features ne dependent pas du decoupage.
- Decoupage en jours de bourse sur les dates distinctes des features ; le train
  commence a la 1re date de features (= 1re date de la base + ~60 jours de
  bourse, le slope 60 necessite 60 jours d'historique).
- Gap de 10 jours de bourse entre fin de train et debut de test.
- n_jobs=-1 ajoute au GridSearchCV (acceleration, resultats identiques).
- La cible (target) necessite 10 jours futurs : les ~10 derniers jours de la
  base n'ont pas de target et sont absents des features.
"""


def write_resume_md() -> None:
    """Genere le resume markdown a partir du CSV de resume."""
    df = pd.read_csv(RESUME_CSV, dtype=str)

    lines = ["# Walk-forward — resume", ""]

    # Tableau markdown reprenant les lignes du CSV
    lines.append("| " + " | ".join(RESUME_COLS) + " |")
    lines.append("|" + "|".join(["---"] * len(RESUME_COLS)) + "|")
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in RESUME_COLS) + " |")

    # Ligne TOTAL : sommes de n_trades, pnl_brut, pnl_net, frais, slippage ;
    # "—" pour retour_pct, win_rate_pct, max_drawdown.
    def somme(col):
        vals = pd.to_numeric(df[col], errors="coerce").dropna()
        return f"{vals.sum():.2f}" if len(vals) else "0.00"

    total = {
        "section": "TOTAL", "train_debut": "", "train_fin": "",
        "test_debut": "", "test_fin": "",
        "n_trades": somme("n_trades"), "pnl_brut": somme("pnl_brut"),
        "pnl_net": somme("pnl_net"), "retour_pct": "—",
        "win_rate_pct": "—", "max_drawdown": "—",
        "frais": somme("frais"), "slippage": somme("slippage"),
    }
    lines.append("| " + " | ".join(str(total[c]) for c in RESUME_COLS) + " |")

    lines += ["", NOTE_IMPLEM]
    RESUME_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Resume markdown ecrit : {RESUME_MD}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t_global = time.time()

    # Config
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    print(f"Config : {cfg}")

    # Etape 0 : cache des features
    full_df = load_features()
    # Dates distinctes triees, en Timestamps pandas (formatage %Y%m%d fiable)
    dates = list(pd.DatetimeIndex(full_df["date"].unique()).sort_values())

    # Grille des sections
    sections = build_sections(dates, cfg)
    print(f"{len(sections)} sections a traiter.")
    deja_faites = load_existing_sections(RESUME_CSV)
    SECTIONS_DIR.mkdir(exist_ok=True)

    for sec in sections:
        t0 = time.time()
        nom = sec["nom"]
        sdir = SECTIONS_DIR / nom

        # Reprise : section deja terminee -> skip
        if (sdir / "knn_backtest.summary.csv").exists():
            print(f"[{nom}] deja terminee, skip.")
            continue

        print(f"[{nom}] train {sec['train_debut']:%Y-%m-%d} -> "
              f"{sec['train_fin']:%Y-%m-%d} | test {sec['test_debut']:%Y-%m-%d} -> "
              f"{sec['test_fin']:%Y-%m-%d}")
        sdir.mkdir(parents=True, exist_ok=True)

        # Decoupage du cache de features sur la fenetre de la section
        df_train = full_df[(full_df["date"] >= sec["train_debut"]) &
                           (full_df["date"] <= sec["train_fin"])]
        df_test = full_df[(full_df["date"] >= sec["test_debut"]) &
                          (full_df["date"] <= sec["test_fin"])]
        df_train.to_csv(sdir / "train_features.csv", index=False)
        df_test.to_csv(sdir / "test_features.csv", index=False)

        echec = False

        # Programme 2 : predictions (SMOTE + GridSearchCV kNN)
        ok2 = run_program(
            ATDIR / "generate_predictions_and_save.py",
            sdir / "log_program2.txt",
            {
                "WF_TRAIN_PATH": str(sdir / "train_features.csv"),
                "WF_TEST_PATH": str(sdir / "test_features.csv"),
                "WF_PRED_OUT": str(sdir / "test_features_with_predictions.csv"),
            },
        )
        if not ok2:
            echec = True

        # Programme 3 : enrichissement OHLCV
        if not echec:
            ok3 = run_program(
                ATDIR / "enrich_predictions.py",
                sdir / "log_program3.txt",
                {
                    "WF_ENRICH_IN": str(sdir / "test_features_with_predictions.csv"),
                    "WF_ENRICH_OUT": str(sdir / "test_features_with_predictions_ohlcv.csv"),
                },
            )
            if not ok3:
                echec = True

        # Programme 4 : backtest (ecrit aussi son propre knn_backtest.log ici)
        if not echec:
            ok4 = run_program(
                ATDIR / "knn_backtest.py",
                sdir / "log_program4.txt",
                {
                    "WF_BACKTEST_CSV": str(sdir / "test_features_with_predictions_ohlcv.csv"),
                },
            )
            if not ok4:
                echec = True

        # Ligne de resume (ERREUR si un programme a echoue ou summary absent)
        if nom not in deja_faites:
            row = build_resume_row(sec, sdir / "knn_backtest.summary.csv")
            append_resume_row(row)
            deja_faites.add(nom)

        print(f"[{nom}] termine en {time.time() - t0:.1f} s"
              + (" (ERREUR)" if echec else ""))

    # Fin : resume markdown
    write_resume_md()
    print(f"Termine en {time.time() - t_global:.1f} s.")


if __name__ == "__main__":
    main()
