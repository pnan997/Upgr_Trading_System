#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etude_sensibilite.py
====================

Etude de sensibilite autour du backtest kNN v5 (knn_backtest.py).

Le script importe knn_backtest (sans jamais appeler main() ni write_summary())
et enchaine des runs de run_backtest() sur les MEMES donnees chargees UNE
seule fois (CSV ~170 Mo).

Etapes
------
0. Non-regression : run de reference (config JSON exacte, seed 42).
   Controles : n_trades == 714 et |pnl_net_total - 6710.56| <= 0.01.
   En cas d'echec : message clair et exit code 2, rien d'autre n'est lance.
1. Controle pnl_brut : sur le journal du run de reference uniquement
   (aucun run supplementaire). Verifications d'arrondi + note explicative.
2. Grille slippage 4x4 : entree_open x (sortie_sl = sortie_gap), 16 runs.
3. Bruit du tirage : 3 scenarios x 5 seeds (42..46), 15 runs.
4. TP/SL alternatifs : 3 variantes (tp_pct, sl_pct), 3 runs.

Usage
-----
    python etude_sensibilite.py
    python etude_sensibilite.py [--only etape1|etape2|etape3|etape4]

L'etape 0 est TOUJOURS executee d'abord (non-negociable).

Sorties (dans le dossier de ce script, rien ailleurs)
-----------------------------------------------------
- etude_sensibilite.md                    : rapport (regenere a chaque run complet)
- etude_sensibilite_grille_slippage.csv  : etape 2, format long
- etude_sensibilite_seeds.csv            : etape 3, format long
- etude_sensibilite_tpsl.csv             : etape 4
- etude_sensibilite_runs/<horodatage>/run_manifest.json : traceabilite
  (config utilisee par run, n_trades, pnl_net). Rien d'autre n'est ecrit :
  pas de write_summary, pas d'export des journaux detailles.
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Import du backtest de reference.
# ATTENTION : l'import ouvre deja un FileHandler sur knn_backtest.log en mode
# "w" (le log est ecrase au moment de l'import). On coupe ensuite TOUT logging
# pour que les run_backtest successifs n'ecrivent nulle part. On n'appelle
# JAMAIS knn_backtest.main() ni knn_backtest.write_summary().
# ---------------------------------------------------------------------------
import knn_backtest as kb

logging.disable(logging.CRITICAL)

STUDY_DIR   = Path(__file__).parent
MD_PATH     = STUDY_DIR / "etude_sensibilite.md"
CSV_GRILLE  = STUDY_DIR / "etude_sensibilite_grille_slippage.csv"
CSV_SEEDS   = STUDY_DIR / "etude_sensibilite_seeds.csv"
CSV_TPSL    = STUDY_DIR / "etude_sensibilite_tpsl.csv"
RUNS_DIR    = STUDY_DIR / "etude_sensibilite_runs"

SEED_REF = 42
N_TRADES_REF = 714
PNL_NET_REF = 6710.56
TOL_PNL = 0.01


# ===========================================================================
# Utilitaires
# ===========================================================================
def fmt_eur(x: float) -> str:
    """Format europeen compact pour le rapport md."""
    return f"{x:,.2f}".replace(",", " ")


def run_one(
    df: pd.DataFrame,
    cfg: dict,
    label: str,
    desc: str,
    counter: Dict[str, int],
    total: int,
    manifest_runs: List[dict],
) -> Tuple[pd.DataFrame, pd.DataFrame, float]:
    """
    Execute un run_backtest avec compteur de progression console et trace
    manifeste. Retourne (equity_df, journal_df, pnl_net_total).
    """
    counter["n"] += 1
    print(f"run {counter['n']}/{total} — {desc}", flush=True)
    equity_df, journal_df, _open = kb.run_backtest(df, cfg)
    pnl_net = float(journal_df["pnl_eur"].sum()) if len(journal_df) else 0.0
    manifest_runs.append({
        "label": label,
        "description": desc,
        "config": cfg,
        "n_trades": int(len(journal_df)),
        "pnl_net": round(pnl_net, 2),
    })
    return equity_df, journal_df, pnl_net


def retour_pct(equity_df: pd.DataFrame, capital_initial: float) -> float:
    """Retour total en % par rapport au capital initial."""
    if equity_df.empty:
        return 0.0
    return (float(equity_df["total_equity"].iloc[-1]) - capital_initial) \
        / capital_initial * 100.0


def md_pivot(df_long: pd.DataFrame, value: str,
             lignes: str, colonnes: str) -> List[str]:
    """Tableau markdown a partir d'un format long."""
    piv = df_long.pivot(index=lignes, columns=colonnes, values=value)
    piv = piv.reindex(index=sorted(piv.index), columns=sorted(piv.columns))
    head = "| " + lignes + r" \ " + colonnes + " | " \
        + " | ".join(f"{c}" for c in piv.columns) + " |"
    sep = "|---" * (len(piv.columns) + 1) + "|"
    lines = [head, sep]
    for idx, row in piv.iterrows():
        cells = " | ".join(fmt_eur(float(v)) for v in row.values)
        lines.append(f"| {idx} | {cells} |")
    return lines


# ===========================================================================
# Etape 0 : non-regression
# ===========================================================================
def etape0(
    df: pd.DataFrame,
    cfg_ref: dict,
    counter: Dict[str, int],
    total: int,
    manifest_runs: List[dict],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run de reference avec la config exacte du JSON (seed 42).
    Controle strict : n_trades == 714 et |pnl_net_total - 6710.56| <= 0.01.
    Si echec : message clair et sys.exit(2), rien d'autre n'est lance.
    """
    t0 = time.time()
    cfg = copy.deepcopy(cfg_ref)
    equity_df, journal_df, pnl_net = run_one(
        df, cfg, "etape0_reference",
        "reference (config JSON, seed 42)", counter, total, manifest_runs)
    n_trades = int(len(journal_df))

    ok_n = (n_trades == N_TRADES_REF)
    ok_pnl = abs(pnl_net - PNL_NET_REF) <= TOL_PNL
    if not (ok_n and ok_pnl):
        print("", flush=True)
        print("ECHEC NON-REGRESSION (etape 0) : rien d'autre n'est lance.", flush=True)
        print(f"  n_trades      = {n_trades} (attendu {N_TRADES_REF})"
              f"  -> {'OK' if ok_n else 'ECART'}", flush=True)
        print(f"  pnl_net_total = {pnl_net:,.2f} (attendu {PNL_NET_REF:,.2f}, "
              f"tolerance +/-{TOL_PNL})  -> {'OK' if ok_pnl else 'ECART'}", flush=True)
        sys.exit(2)

    print(f"  non-regression OK : n_trades={n_trades}, "
          f"pnl_net_total={pnl_net:,.2f}", flush=True)
    return equity_df, journal_df


# ===========================================================================
# Etape 1 : controle pnl_brut (aucun run supplementaire)
# ===========================================================================
def etape1(journal_ref: pd.DataFrame) -> List[str]:
    """
    Controles sur le journal du run de reference :
    - pnl_brut == nb_actions * (prix_theorique_sortie - prix_theorique_entree)
      a +/-0.02 pres (arrondis) ;
    - somme pnl_brut vs somme (pnl_eur + slippage_cout + frais_entree
      + frais_sortie) : ecarts toleres si arrondi par trade.
    Produit un petit tableau de controle (max ecart par trade, ecart total).
    """
    out: List[str] = ["## Etape 1 — Contrôle pnl_brut (run de référence)", ""]

    if journal_ref.empty:
        out.append("Journal vide : contrôles impossibles.")
        out.append("")
        return out

    # Controle 1 : pnl_brut = N * (P_sortie_theo - P_entree_theo)
    ecart_brut = (
        journal_ref["pnl_brut"]
        - journal_ref["nb_actions"]
          * (journal_ref["prix_theorique_sortie"]
             - journal_ref["prix_theorique_entree"])
    )
    max_ecart_brut = float(ecart_brut.abs().max())
    n_viol = int((ecart_brut.abs() > 0.02).sum())

    # Controle 2 : recomposition pnl_net = brut - slippage - frais
    somme_brut = float(journal_ref["pnl_brut"].sum())
    somme_recomp = float(
        journal_ref["pnl_eur"].sum()
        + journal_ref["slippage_cout"].sum()
        + journal_ref["frais_entree"].sum()
        + journal_ref["frais_sortie"].sum()
    )
    ecart_total = somme_brut - somme_recomp
    ecart_recomp_trade = (
        journal_ref["pnl_brut"]
        - journal_ref["slippage_cout"]
        - journal_ref["frais_entree"]
        - journal_ref["frais_sortie"]
        - journal_ref["pnl_eur"]
    )
    max_ecart_recomp = float(ecart_recomp_trade.abs().max())

    out.append("| Contrôle | Valeur |")
    out.append("|---|---|")
    out.append(f"| Max écart par trade : pnl_brut vs N×(P_tho_sortie−P_tho_entrée) "
               f"(tolérance ±0.02) | {max_ecart_brut:.4f} |")
    out.append(f"| Nombre de trades hors tolérance ±0.02 | {n_viol} |")
    out.append(f"| Max écart par trade : brut−slippage−frais vs pnl_eur "
               f"(arrondi par trade) | {max_ecart_recomp:.4f} |")
    out.append(f"| Somme pnl_brut | {fmt_eur(somme_brut)} |")
    out.append(f"| Somme (pnl_eur + slippage_cout + frais_entree + frais_sortie) "
               f"| {fmt_eur(somme_recomp)} |")
    out.append(f"| Écart total (somme brut − somme recomposée) | {ecart_total:.4f} |")
    out.append("")
    verdict = "OK" if (n_viol == 0 and abs(ecart_total) <= 0.02 * len(journal_ref)) \
        else "à examiner"
    out.append(f"Verdict global : **{verdict}** "
               f"({len(journal_ref)} trades contrôlés).")
    out.append("")

    out.append("**Note — définition de pnl_brut (v5)** : pnl_brut = PnL aux prix "
               "théoriques avec le **même nombre d'actions** que le trade réel, "
               "soit `N × (prix_théorique_sortie − prix_théorique_entrée)`.")
    out.append("")
    out.append("L'ancien écart (11684.81 vs 11685.72) venait du nombre d'actions "
               "calculé sur le prix **après** slippage (arrondi floor différent), "
               "combiné à un pnl_brut recalculé via `S = N × entry_exec`.")
    out.append("")
    return out


# ===========================================================================
# Etape 2 : grille slippage 4x4
# ===========================================================================
def etape2(
    df: pd.DataFrame,
    cfg_ref: dict,
    counter: Dict[str, int],
    total: int,
    manifest_runs: List[dict],
) -> List[str]:
    """
    Grille slippage : entree_open x (sortie_sl = sortie_gap), produit
    cartesien 4x4 = 16 runs. Filtre prix_min 9.0 actif, frais actifs,
    slippage actif, seed 42, sortie_tp = 0.0.
    """
    t0 = time.time()
    entrees = [0.0, 0.00025, 0.0005, 0.001]
    sorties = [0.0, 0.0005, 0.001, 0.002]

    rows: List[dict] = []
    for e in entrees:
        for s in sorties:
            cfg = copy.deepcopy(cfg_ref)
            cfg["seed"] = SEED_REF
            cfg["prix_min"] = 9.0
            cfg.setdefault("frais", {})["actif"] = True
            cfg.setdefault("slippage", {})["actif"] = True
            cfg["slippage"]["entree_open"] = e
            cfg["slippage"]["sortie_sl"] = s
            cfg["slippage"]["sortie_gap"] = s
            cfg["slippage"]["sortie_tp"] = 0.0

            desc = f"grille slippage entree_open={e} sortie_sl/gap={s}"
            _eq, _jr, pnl_net = run_one(
                df, cfg, "etape2_grille", desc, counter, total, manifest_runs)
            rows.append({
                "entree_open": e,
                "sortie_sl": s,
                "pnl_net": round(pnl_net, 2),
                "retour_pct": round(retour_pct(_eq, float(cfg_ref["capital_initial"])), 4),
            })

    df_long = pd.DataFrame(rows)
    df_long.to_csv(CSV_GRILLE, index=False, encoding="utf-8")

    out: List[str] = ["## Etape 2 — Grille slippage (16 runs)", ""]
    out.append("Config : filtre prix_min 9.0 actif, frais actifs, slippage actif, "
               "seed 42, sortie_tp = 0.0. Lignes = entree_open, "
               "colonnes = sortie_sl (= sortie_gap).")
    out.append("")
    out.append("### pnl_net (EUR)")
    out.append("")
    out.extend(md_pivot(df_long, "pnl_net", "entree_open", "sortie_sl"))
    out.append("")
    out.append("### retour_pct (%)")
    out.append("")
    out.extend(md_pivot(df_long, "retour_pct", "entree_open", "sortie_sl"))
    out.append("")

    # Frontiere de rentabilite
    negatifs = df_long[df_long["pnl_net"] < 0.0]
    positifs = df_long[df_long["pnl_net"] >= 0.0]
    out.append("### Frontière de rentabilité")
    out.append("")
    if len(negatifs):
        out.append("Combinaisons où pnl_net passe **négatif** :")
        out.append("")
        for _, r in negatifs.iterrows():
            out.append(f"- entree_open={r['entree_open']}, "
                       f"sortie_sl/gap={r['sortie_sl']} → pnl_net = "
                       f"{fmt_eur(float(r['pnl_net']))} EUR")
        out.append("")
    else:
        out.append("Aucune combinaison négative sur la grille explorée.")
        out.append("")
    if len(positifs):
        # Definition : plus grande combinaison encore positive = celle qui
        # maximise (entree_open + sortie_sl), departage par entree_open
        # puis sortie_sl.
        pos = positifs.copy()
        pos["_somme"] = pos["entree_open"] + pos["sortie_sl"]
        best = pos.sort_values(["_somme", "entree_open", "sortie_sl"],
                               ascending=False).iloc[0]
        out.append(
            f"Plus grande combinaison encore positive (max entree_open+sortie_sl) : "
            f"entree_open={best['entree_open']}, sortie_sl/gap={best['sortie_sl']} "
            f"→ pnl_net = {fmt_eur(float(best['pnl_net']))} EUR "
            f"(retour {float(best['retour_pct']):.2f}%).")
        out.append("")

    print(f"  etape 2 terminee en {time.time()-t0:.1f} s", flush=True)
    return out


# ===========================================================================
# Etape 3 : bruit du tirage (seeds)
# ===========================================================================
def etape3(
    df: pd.DataFrame,
    cfg_ref: dict,
    counter: Dict[str, int],
    total: int,
    manifest_runs: List[dict],
) -> List[str]:
    """
    Bruit du tirage : 5 seeds (42..46) x 3 scenarios = 15 runs.
    Slippage = valeur actuelle de la config (entree_open 0.0005,
    sortie_sl 0.001, sortie_gap 0.001, sortie_tp 0).
    """
    t0 = time.time()
    seeds = [42, 43, 44, 45, 46]

    scenarios: Dict[str, Tuple[str, dict]] = {}

    cfg_a = copy.deepcopy(cfg_ref)
    cfg_a["prix_min"] = None          # ou 0 : filtre desactive
    cfg_a["frais"]["actif"] = False
    cfg_a["slippage"]["actif"] = False
    scenarios["a_tout_desactive"] = (
        "(a) tout desactive : prix_min=None, frais off, slippage off", cfg_a)

    cfg_b = copy.deepcopy(cfg_ref)
    cfg_b["prix_min"] = 9.0
    cfg_b["frais"]["actif"] = False
    cfg_b["slippage"]["actif"] = False
    scenarios["b_filtre_seul"] = ("(b) filtre seul : prix_min=9.0, frais off, "
                                  "slippage off", cfg_b)

    cfg_d = copy.deepcopy(cfg_ref)
    scenarios["d_reference"] = ("(d) filtre+frais+slippage : config de reference",
                                cfg_d)

    rows: List[dict] = []
    for seed in seeds:
        for key, (desc_s, base_cfg) in scenarios.items():
            cfg = copy.deepcopy(base_cfg)
            cfg["seed"] = seed
            desc = f"seeds {key} seed={seed}"
            _eq, _jr, pnl_net = run_one(
                df, cfg, f"etape3_{key}", desc, counter, total, manifest_runs)
            rows.append({"seed": seed, "scenario": key,
                         "pnl_net": round(pnl_net, 2)})

    df_long = pd.DataFrame(rows)
    df_long.to_csv(CSV_SEEDS, index=False, encoding="utf-8")

    out: List[str] = ["## Etape 3 — Bruit du tirage (15 runs)", ""]
    out.append("Slippage = valeur actuelle de la config (entree_open 0.0005, "
               "sortie_sl 0.001, sortie_gap 0.001, sortie_tp 0). "
               "Chiffres seuls, pas de conclusion.")
    out.append("")
    out.append("| Seed | (a) tout désactivé | (b) filtre seul | (d) référence |")
    out.append("|---|---|---|---|")
    piv = df_long.pivot(index="seed", columns="scenario", values="pnl_net")
    for seed in seeds:
        cells = " | ".join(
            fmt_eur(float(piv.loc[seed, k])) if k in piv.columns else "-"
            for k in ("a_tout_desactive", "b_filtre_seul", "d_reference"))
        out.append(f"| {seed} | {cells} |")
    out.append("| **moyenne** | " + " | ".join(
        f"**{fmt_eur(float(df_long[df_long['scenario']==k]['pnl_net'].mean()))}**"
        for k in ("a_tout_desactive", "b_filtre_seul", "d_reference")) + " |")
    out.append("| **écart-type (ddof=1)** | " + " | ".join(
        f"**{float(df_long[df_long['scenario']==k]['pnl_net'].std(ddof=1)):.2f}**"
        for k in ("a_tout_desactive", "b_filtre_seul", "d_reference")) + " |")
    out.append("")
    print(f"  etape 3 terminee en {time.time()-t0:.1f} s", flush=True)
    return out


# ===========================================================================
# Etape 4 : TP/SL alternatifs
# ===========================================================================
def etape4(
    df: pd.DataFrame,
    cfg_ref: dict,
    counter: Dict[str, int],
    total: int,
    manifest_runs: List[dict],
) -> List[str]:
    """
    TP/SL alternatifs : 3 variantes (tp_pct, sl_pct), seed 42, config de
    reference (filtre + frais + slippage actuels). Tout passe par cfg.
    """
    t0 = time.time()
    variantes = [(0.015, 0.006), (0.025, 0.010), (0.040, 0.020)]

    rows: List[dict] = []
    for tp, sl in variantes:
        cfg = copy.deepcopy(cfg_ref)
        cfg["seed"] = SEED_REF
        cfg["tp_pct"] = tp
        cfg["sl_pct"] = sl

        desc = f"TP/SL tp={tp} sl={sl}"
        _eq, jr, _pnl = run_one(
            df, cfg, "etape4_tpsl", desc, counter, total, manifest_runs)

        n = len(jr)
        win_rate = float((jr["pnl_eur"] > 0).mean() * 100.0) if n else 0.0
        rows.append({
            "tp_pct": tp,
            "sl_pct": sl,
            "n_trades": n,
            "win_rate_pct": round(win_rate, 2),
            "pnl_brut": round(float(jr["pnl_brut"].sum()), 2) if n else 0.0,
            "frais": round(float(jr["frais_entree"].sum()
                                 + jr["frais_sortie"].sum()), 2) if n else 0.0,
            "slippage": round(float(jr["slippage_cout"].sum()), 2) if n else 0.0,
            "pnl_net": round(float(jr["pnl_eur"].sum()), 2) if n else 0.0,
            "retour_pct": round(retour_pct(_eq, float(cfg_ref["capital_initial"])), 4),
        })

    df_res = pd.DataFrame(rows)
    df_res.to_csv(CSV_TPSL, index=False, encoding="utf-8")

    out: List[str] = ["## Etape 4 — TP/SL alternatifs (3 runs)", ""]
    out.append("Seed 42, config de référence (filtre + frais + slippage actuels). "
               "Variantes uniquement via cfg (tp_pct / sl_pct).")
    out.append("")
    out.append("| tp_pct | sl_pct | n_trades | win_rate_pct | pnl_brut | frais | "
               "slippage | pnl_net | retour_pct |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for _, r in df_res.iterrows():
        out.append(
            f"| {r['tp_pct']} | {r['sl_pct']} | {int(r['n_trades'])} | "
            f"{r['win_rate_pct']:.2f} | {fmt_eur(float(r['pnl_brut']))} | "
            f"{fmt_eur(float(r['frais']))} | {fmt_eur(float(r['slippage']))} | "
            f"{fmt_eur(float(r['pnl_net']))} | {float(r['retour_pct']):.2f} |")
    out.append("")
    print(f"  etape 4 terminee en {time.time()-t0:.1f} s", flush=True)
    return out


# ===========================================================================
# Rapport markdown
# ===========================================================================
def write_md(
    sections: Dict[str, List[str]],
    steps_run: List[str],
    cfg_ref: dict,
    durees: Dict[str, float],
    duree_globale: float,
) -> None:
    """Regenere entierement etude_sensibilite.md avec les sections calculees."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = [
        "# Étude de sensibilité — backtest kNN v5",
        "",
        f"Généré le {now}.",
        "",
        "Config de référence : `knn_backtest_config.json` "
        f"(seed {cfg_ref['seed']}, tp_pct {cfg_ref['tp_pct']}, "
        f"sl_pct {cfg_ref['sl_pct']}, prix_min {cfg_ref.get('prix_min')}, "
        f"frais.actif {cfg_ref.get('frais', {}).get('actif')}, "
        f"slippage.actif {cfg_ref.get('slippage', {}).get('actif')}).",
        "",
    ]
    skipped = [s for s in ("etape1", "etape2", "etape3", "etape4") if s not in steps_run]
    if skipped:
        lines.append(f"Étapes non exécutées lors de cette invocation "
                     f"(--only) : {', '.join(skipped)}.")
        lines.append("")

    for key in ("etape1", "etape2", "etape3", "etape4"):
        if key in sections and sections[key]:
            lines.extend(sections[key])

    lines.append("## Temps d'exécution")
    lines.append("")
    lines.append("| Étape | Durée (s) |")
    lines.append("|---|---|")
    for k, v in durees.items():
        lines.append(f"| {k} | {v:.1f} |")
    lines.append(f"| **Total** | **{duree_globale:.1f}** |")
    lines.append("")
    lines.append("Un temps par run > 120 s est à surveiller "
                 f"({len(durees)} étape(s), cf. console pour le détail par run).")
    lines.append("")

    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


# ===========================================================================
# Main
# ===========================================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Etude de sensibilite du backtest kNN v5")
    parser.add_argument("--only", choices=["etape1", "etape2", "etape3", "etape4"],
                        default=None,
                        help="N'exécuter qu'une étape (l'étape 0 non-régression "
                             "est toujours exécutée avant).")
    args = parser.parse_args()

    t0 = time.time()
    steps_run: List[str] = []
    durees: Dict[str, float] = {}

    cfg_ref = kb.load_config(kb.CONFIG_PATH)

    # Determination du nombre total de runs (pour le compteur console)
    total = 1  # etape 0
    if args.only in (None, "etape2"):
        total += 16
    if args.only in (None, "etape3"):
        total += 15
    if args.only in (None, "etape4"):
        total += 3
    counter = {"n": 0}
    manifest_runs: List[dict] = []

    print(f"Chargement des données (une seule fois, ~170 Mo) : "
          f"{kb.CSV_PATH}", flush=True)
    df = kb.load_data(kb.CSV_PATH)
    print(f"  {len(df):,} lignes chargées.", flush=True)

    # --- Etape 0 (toujours) ---
    ts = time.time()
    equity_ref, journal_ref = etape0(df, cfg_ref, counter, total, manifest_runs)
    durees["etape0_non_regression"] = time.time() - ts
    steps_run.append("etape0")
    sections: Dict[str, List[str]] = {}

    # --- Etape 1 ---
    if args.only in (None, "etape1"):
        ts = time.time()
        sections["etape1"] = etape1(journal_ref)
        durees["etape1_controle_pnl_brut"] = time.time() - ts
        steps_run.append("etape1")

    # --- Etape 2 ---
    if args.only in (None, "etape2"):
        ts = time.time()
        sections["etape2"] = etape2(df, cfg_ref, counter, total, manifest_runs)
        durees["etape2_grille_slippage"] = time.time() - ts
        steps_run.append("etape2")

    # --- Etape 3 ---
    if args.only in (None, "etape3"):
        ts = time.time()
        sections["etape3"] = etape3(df, cfg_ref, counter, total, manifest_runs)
        durees["etape3_bruit_seeds"] = time.time() - ts
        steps_run.append("etape3")

    # --- Etape 4 ---
    if args.only in (None, "etape4"):
        ts = time.time()
        sections["etape4"] = etape4(df, cfg_ref, counter, total, manifest_runs)
        durees["etape4_tpsl"] = time.time() - ts
        steps_run.append("etape4")

    # --- Manifeste de tracabilite ---
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / horodatage
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "horodatage": horodatage,
        "etapes_executees": steps_run,
        "n_runs": len(manifest_runs),
        "runs": manifest_runs,
    }
    with open(run_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # --- Rapport md ---
    duree_globale = time.time() - t0
    write_md(sections, steps_run, cfg_ref, durees, duree_globale)

    print("", flush=True)
    print("=== Etude terminée ===", flush=True)
    for k, v in durees.items():
        print(f"  {k:<28s} {v:8.1f} s", flush=True)
    print(f"  {'TOTAL':<28s} {duree_globale:8.1f} s", flush=True)
    print(f"Sorties : {MD_PATH.name}, "
          f"{CSV_GRILLE.name if 'etape2' in steps_run else '-'}, "
          f"{CSV_SEEDS.name if 'etape3' in steps_run else '-'}, "
          f"{CSV_TPSL.name if 'etape4' in steps_run else '-'}, "
          f"manifeste -> {run_dir}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
