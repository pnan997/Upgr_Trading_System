"""
download_delta.py — Mise à jour quotidienne delta OHLCV
========================================================
Philosophie :
  - Silence sur les trains à l'heure (COMPLETED)
  - Rapport détaillé sur WARNING et ERROR uniquement
  - Chunking par date_fin_dispo (même start_date = même batch yfinance)
  - INSERT bulk DuckDB (pas de connexion par ticker)
  - Validation OHLCV stricte : tout zéro = ERROR
  - Mode --retry-errors : traite uniquement les tickers en ERROR

Usage :
  python download_delta.py                  # batch standard
  python download_delta.py --retry-errors   # relance les ERROR uniquement
  python download_delta.py --batch-size 200 # taille de chunk (défaut 250)
"""

import duckdb
import yfinance as yf
import pandas as pd
from datetime import date, datetime, timedelta
import argparse
import sys
import os
from collections import defaultdict
import sys as _sys
_sys.path.insert(0, os.environ["TS_ROOT"])
try:
    from Utils.sharpe import (
        create_tables_if_needed as _sharpe_create_tables,
        update_rf_today          as _sharpe_update_rf,
        compute_and_store_sharpe as _sharpe_compute,
    )
    _SHARPE_AVAILABLE = True
except ImportError as _e:
    _SHARPE_AVAILABLE = False
    print(f"[WARN] Utils/sharpe.py non disponible — SR ignoré : {_e}")

try:
    from Utils.ma_check import check_ma_activity, is_confirmed_delisting, load_ticker_company_map
    _MA_CHECK_AVAILABLE = True
except ImportError as _e:
    _MA_CHECK_AVAILABLE = False
    print(f"[WARN] Utils/ma_check.py non disponible — verification M&A ignorée : {_e}")

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH        = "/Users/Shared/tickers_meta.db"
ERROR_CSV_PATH = os.path.join(os.environ["TS_ROOT"], "tickers_errors.csv")
BATCH_SIZE_DEFAULT = 250

# Jours fériés US fixes (NYSE) — année courante + année précédente
# Format : (mois, jour)
US_HOLIDAYS_FIXED = {
    (1, 1),   # New Year's Day
    (7, 4),   # Independence Day
    (12, 25), # Christmas
}

# ── Utilitaires calendrier ─────────────────────────────────────────────────────

def is_business_day(d: date) -> bool:
    """Vrai si d est un jour ouvré boursier (lun-ven, hors fériés fixes)."""
    if d.weekday() >= 5:  # samedi=5, dimanche=6
        return False
    if (d.month, d.day) in US_HOLIDAYS_FIXED:
        return False
    return True


def next_business_day(d: date) -> date:
    """Retourne le premier jour ouvré strictement après d."""
    candidate = d + timedelta(days=1)
    while not is_business_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def prev_business_day(d: date) -> date:
    """Retourne le dernier jour ouvré strictement avant d."""
    candidate = d - timedelta(days=1)
    while not is_business_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


def last_completed_business_day() -> date:
    """
    Dernier jour de bourse dont les données sont disponibles.
    yfinance publie J-1 → on prend avant-hier si aujourd'hui n'est pas ouvré,
    sinon hier.
    """
    today = date.today()
    return prev_business_day(today)


# ── Validation OHLCV ───────────────────────────────────────────────────────────

def validate_ohlcv(df: pd.DataFrame) -> list[str]:
    """
    Valide chaque ligne du DataFrame OHLCV.
    Retourne une liste de messages d'anomalie (vide = tout OK).
    Règles :
      - Open, High, Low, Close > 0
      - Volume > 0
      - High >= Low
      - High >= Open et High >= Close
    """
    anomalies = []

    zero_price = df[(df["Open"] <= 0) | (df["High"] <= 0) |
                    (df["Low"] <= 0)  | (df["Close"] <= 0)]
    if not zero_price.empty:
        dates = zero_price["Date"].dt.date.tolist()
        anomalies.append(f"prix nul ou négatif sur {len(zero_price)} séance(s) : {dates}")

    zero_vol = df[df["Volume"] <= 0]
    if not zero_vol.empty:
        dates = zero_vol["Date"].dt.date.tolist()
        anomalies.append(f"volume nul ou négatif sur {len(zero_vol)} séance(s) : {dates}")

    incoherent = df[df["High"] < df["Low"]]
    if not incoherent.empty:
        dates = incoherent["Date"].dt.date.tolist()
        anomalies.append(f"High < Low sur {len(incoherent)} séance(s) : {dates}")

    hl_open = df[df["High"] < df["Open"]]
    hl_close = df[df["High"] < df["Close"]]
    if not hl_open.empty or not hl_close.empty:
        cnt = max(len(hl_open), len(hl_close))
        anomalies.append(f"High < Open/Close sur {cnt} séance(s)")

    return anomalies


# ── Chargement référentiel ─────────────────────────────────────────────────────

def load_ticker_groups(retry_errors: bool) -> dict[date, list[str]]:
    """
    Charge les tickers à traiter depuis tickers_meta.
    Retourne un dict { start_date: [symbol, ...] }
    groupé par date de début de la fenêtre à télécharger.

    En mode normal    : tickers COMPLETED dont date_fin_dispo < last_business_day
    En mode retry     : tickers ERROR uniquement
    """
    last_bd = last_completed_business_day()

    conn = duckdb.connect(DB_PATH)

    if retry_errors:
        rows = conn.execute("""
            SELECT symbol, date_fin_dispo
            FROM tickers_meta
            WHERE statut = 'ERROR'
            ORDER BY date_fin_dispo ASC NULLS FIRST, symbol ASC
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT symbol, date_fin_dispo
            FROM tickers_meta
            WHERE statut IN ('COMPLETED', 'WARNING')
              AND (date_fin_dispo IS NULL OR date_fin_dispo < ?)
            ORDER BY date_fin_dispo ASC NULLS FIRST, symbol ASC
        """, [last_bd]).fetchall()

    conn.close()

    # Grouper par start_date calculé
    groups: dict[date, list[str]] = defaultdict(list)
    for symbol, last_date in rows:
        if last_date is None:
            start = last_bd - timedelta(days=365 * 5)
        else:
            start = next_business_day(last_date)

        # Si start > last_bd : déjà à jour, on skip
        if start > last_bd:
            continue

        groups[start].append(symbol)

    return groups


# ── Téléchargement et insertion ────────────────────────────────────────────────

def chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def process_chunk(symbols: list[str], start: date, end: date,
                   retry_errors: bool = False, ticker_company_map: dict | None = None) -> dict:
    """
    Télécharge un chunk de tickers avec la même fenêtre start→end.
    Insère en bulk dans DuckDB.
    Retourne les compteurs et les rapports WARNING/ERROR.
    """
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = {"success": 0, "warnings": [], "errors": [], "delisted": []}

    # ── Téléchargement batch ───────────────────────────────────────────────────
    try:
        raw = yf.download(
            tickers=symbols,
            start=start.strftime("%Y-%m-%d"),
            end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),  # end exclusif
            progress=False,
            auto_adjust=True,
            threads=False,  # threads=False pour éviter les problèmes de corruption de cache yfinance
            group_by="ticker",
        )
    except Exception as e:
        # Erreur globale : tous les tickers du chunk en ERROR
        conn = duckdb.connect(DB_PATH)
        for sym in symbols:
            conn.execute("""
                UPDATE tickers_meta
                SET statut='ERROR', dernier_essai=?, message_erreur=?
                WHERE symbol=?
            """, [today_str, f"yfinance batch exception: {e}", sym])
        conn.close()
        results["errors"] += [(s, f"batch exception: {e}") for s in symbols]
        return results

    # ── Erreurs signalées par yfinance ────────────────────────────────────────
    yf_errors = {}
    try:
        yf_errors = dict(yf.shared._ERRORS) if yf.shared._ERRORS else {}
    except Exception:
        pass

    # ── Traitement par ticker ──────────────────────────────────────────────────
    conn = duckdb.connect(DB_PATH)

    for sym in symbols:

        # Erreur yfinance explicite
        if sym in yf_errors:
            msg = str(yf_errors[sym])
            conn.execute("""
                UPDATE tickers_meta
                SET statut='ERROR', dernier_essai=?, message_erreur=?
                WHERE symbol=?
            """, [today_str, msg, sym])
            results["errors"].append((sym, msg))
            continue

# Extraire le sous-DataFrame
        try:
            if len(symbols) == 1:
                df = raw.copy()
            else:
                df = raw[sym].copy() if sym in raw.columns.get_level_values(0) else pd.DataFrame()

            # ── Aplatir le MultiIndex de colonnes si yfinance l'a produit ──
            # yfinance peut retourner des colonnes sous forme (ticker, OHLCV)
            # ou (OHLCV, ticker) selon la version et le nombre de tickers.
            # On ramène toujours à un index plat : Open, High, Low, Close, Volume
            if isinstance(df.columns, pd.MultiIndex):
                # Cas (OHLCV, ticker) : le nom OHLCV est au niveau 0
                if df.columns.get_level_values(0)[0] in ('Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume'):
                    df.columns = df.columns.get_level_values(0)
                # Cas (ticker, OHLCV) : le nom OHLCV est au niveau 1
                else:
                    df.columns = df.columns.get_level_values(1)

        except Exception as e:
            conn.execute("""
                UPDATE tickers_meta
                SET statut='ERROR', dernier_essai=?, message_erreur=?
                WHERE symbol=?
            """, [today_str, f"extraction DataFrame: {e}", sym])
            results["errors"].append((sym, f"extraction DataFrame: {e}"))
            continue

        df = df.dropna(how="all").reset_index()

        # Filtrer sur la fenêtre start→end
        if df.empty or "Date" not in df.columns:
        # Téléchargement vide (ticker probablement delisted) : on saute
        # le filtre de date, df reste vide, la logique DELISTED ci-dessous
        # prend le relais normalement.
            pass
        else:
            df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]

        if df.empty:
            # Pas de données → candidat DELISTED (en retry) sinon ERROR
            msg = f"aucune donnée retournée pour {start} → {end}"

            if retry_errors and _MA_CHECK_AVAILABLE and ticker_company_map and sym in ticker_company_map:
                verdict = check_ma_activity(sym, ticker_company_map[sym])
                if is_confirmed_delisting(verdict):
                    conn.execute("""
                        UPDATE tickers_meta
                        SET statut='DELISTED', dernier_essai=?, message_erreur=?
                        WHERE symbol=?
                    """, [today_str, f"{verdict['operation_type']}: {verdict['summary']}", sym])
                    results.setdefault("delisted", []).append((sym, verdict))
                    continue

            conn.execute("""
                UPDATE tickers_meta
                SET statut='ERROR', dernier_essai=?, message_erreur=?
                WHERE symbol=?
            """, [today_str, msg, sym])
            results["errors"].append((sym, msg))
            continue
        # Séances sans prix (NaN) : ne pas les insérer, pour que le jour soit
        # retéléchargé au prochain run (date_fin_dispo n'avance pas dessus)
        price_cols = ["Open", "High", "Low", "Close"]
        nan_rows = df[df[price_cols].isna().any(axis=1)]
        df = df.drop(nan_rows.index)
        nan_msg = None
        if not nan_rows.empty:
            nan_msg = (f"{len(nan_rows)} séance(s) sans prix (NaN) ignorée(s) : "
                       f"{nan_rows['Date'].dt.date.tolist()}")
        if df.empty:
            conn.execute("""
                UPDATE tickers_meta
                SET statut='WARNING', dernier_essai=?, message_erreur=?
                WHERE symbol=?
            """, [today_str, nan_msg, sym])
            results["warnings"].append((sym, 0, [nan_msg]))
            continue            
        # Validation OHLCV
        anomalies = validate_ohlcv(df)
        if nan_msg:
            anomalies.append(nan_msg)
        statut = "WARNING" if anomalies else "COMPLETED"

        # Nom de table — sanitisation complète (., -, ^)
        table_name = f"ohlcv_{sym.replace('.', '_').replace('-', '_')}"
        tname = f'"{table_name}"'
        # INSERT bulk
        try:
            table_exists = conn.execute(f"""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = '{table_name}'
            """).fetchone() is not None

            if not table_exists:
                conn.execute(f"CREATE TABLE {tname} AS SELECT * FROM df")
            else:
                # Calcul date max en Python (agrégat dans WHERE rejeté par DuckDB)
                row = conn.execute(f"SELECT COALESCE(MAX(Date)::DATE, '1900-01-01'::DATE) FROM {tname}").fetchone()
                last_date_in_db = str(row[0])
                conn.execute(f"""
                    INSERT INTO {tname}
                    SELECT * FROM df
                    WHERE Date::DATE > '{last_date_in_db}'::DATE
                """)

            total_rows = conn.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
            min_date   = df["Date"].dt.date.min()
            max_date   = df["Date"].dt.date.max()
            nb_new     = len(df)

            conn.execute("""
                UPDATE tickers_meta
                SET
                    date_debut_dispo   = CASE WHEN date_debut_dispo IS NULL THEN ? ELSE date_debut_dispo END,
                    date_fin_dispo     = ?,
                    nb_enregistrements = ?,
                    statut             = ?,
                    dernier_essai      = ?,
                    message_erreur     = ?
                WHERE symbol = ?
            """, [
                min_date, max_date, total_rows,
                statut, today_str,
                " | ".join(anomalies) if anomalies else None,
                sym
            ])

            if statut == "WARNING":
                results["warnings"].append((sym, nb_new, anomalies))
            else:
                results["success"] += 1
            # Calcul SR pour le(s) nouveau(x) jour(s) insérés
            if _SHARPE_AVAILABLE:
                try:
                    _sharpe_compute(sym, conn, only_new=True)
                except Exception as _e_sr:
                    # Erreur SR non bloquante — l'OHLCV est déjà inséré
                    # On loggue discrètement sans polluer le rapport
                    pass
                
        except Exception as e:
            conn.execute("""
                UPDATE tickers_meta
                SET statut='ERROR', dernier_essai=?, message_erreur=?
                WHERE symbol=?
            """, [today_str, f"INSERT DuckDB: {e}", sym])
            results["errors"].append((sym, f"INSERT DuckDB: {e}"))

    conn.close()
    return results


# ── Rapport final ──────────────────────────────────────────────────────────────

def print_report(run_date: str, total: int, success: int,
                 all_warnings: list, all_errors: list, all_delisted: list = None):
    all_delisted = all_delisted or []
    print()
    print("=" * 60)
    print(f"RAPPORT DELTA OHLCV — {run_date}")
    print("=" * 60)
    print(f"  Tickers traités    : {total}")
    print(f"  COMPLETED (OK)     : {success}")
    print(f"  WARNING            : {len(all_warnings)}")
    print(f"  ERROR              : {len(all_errors)}")
    print(f"  DELISTED (M&A)     : {len(all_delisted)}")
    print()

    if all_delisted:
        print("DELISTED — CONFIRMÉ PAR RECHERCHE M&A")
        print("-" * 60)
        for sym, verdict in all_delisted:
            print(f"  {sym:<10} : {verdict['operation_type']} — {verdict['summary']}")
        print()

    if all_warnings:
        print("AVERTISSEMENTS — DONNÉES SUSPECTES")
        print("-" * 60)
        for sym, nb_new, anomalies in all_warnings:
            print(f"  {sym:<10} ({nb_new} ligne(s) insérée(s))")
            for a in anomalies:
                print(f"             → {a}")
        print()

    if all_errors:
        print("ERREURS — NON CHARGÉS")
        print("-" * 60)
        for sym, msg in all_errors:
            print(f"  {sym:<10} : {msg}")
        print()

    if all_warnings or all_errors:
        print("ACTION RECOMMANDÉE")
        print("-" * 60)
        if all_errors:
            print("  Relancer avec --retry-errors avant le prochain batch standard")
        if all_warnings:
            print("  Vérifier manuellement les tickers en WARNING")
        print()

    print("=" * 60)


def export_error_csv(all_errors: list):
    """Exporte les tickers en erreur dans un CSV."""
    if not all_errors:
        return
    conn = duckdb.connect(DB_PATH)
    result = conn.execute("""
        SELECT symbol, statut, dernier_essai, message_erreur
        FROM tickers_meta
        WHERE statut = 'ERROR'
        ORDER BY symbol
    """).fetchdf()
    conn.close()
    if not result.empty:
        result.to_csv(ERROR_CSV_PATH, index=False)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if _SHARPE_AVAILABLE:
        try:
            _con_init = duckdb.connect(DB_PATH)
            _sharpe_create_tables(_con_init)   # no-op si tables déjà présentes
            _rf = _sharpe_update_rf(_con_init)  # télécharge ^IRX une seule fois
            _con_init.close()
            if _rf is not None:
                print(f"SR — rf du jour (^IRX) : {_rf:.4%} annualisé")
            else:
                print("SR — ^IRX non disponible, dernière valeur connue utilisée")
        except Exception as _e:
            print(f"SR — initialisation échouée (batch continue) : {_e}")
    parser = argparse.ArgumentParser(
        description="Mise à jour delta OHLCV — batch quotidien"
    )
    parser.add_argument("--retry-errors", action="store_true",
                        help="Traite uniquement les tickers en statut ERROR")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT,
                        help=f"Tickers par chunk yfinance (défaut: {BATCH_SIZE_DEFAULT})")
    args = parser.parse_args()

    run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    end_date = last_completed_business_day()

    print(f"Démarrage — {run_date}")
    print(f"Dernier jour ouvré cible : {end_date}")
    if args.retry_errors:
        print("Mode : RETRY ERRORS")
    print()

    # Charger les groupes par start_date
    groups = load_ticker_groups(args.retry_errors)

    if not groups:
        print("Aucun ticker à traiter.")
        sys.exit(0)

    total_tickers = sum(len(v) for v in groups.values())
    print(f"Tickers à traiter : {total_tickers} répartis en {len(groups)} groupe(s) de dates")
    print()

    # Charger la correspondance ticker->company (utile seulement en retry M&A)
    ticker_company_map = {}
    if _MA_CHECK_AVAILABLE and args.retry_errors:
        ticker_company_map = load_ticker_company_map()
        print(f"Correspondance ticker→company chargée : {len(ticker_company_map)} entrées")

    # Accumulateurs pour le rapport
    total_success = 0
    all_warnings  = []
    all_errors    = []
    all_delisted  = []
    total_processed = 0

    # Traiter groupe par groupe (même start_date = même fenêtre yfinance)
    for start_date in sorted(groups.keys()):
        symbols = groups[start_date]
        print(f"[{start_date} → {end_date}] {len(symbols)} ticker(s)")

        for chunk in chunks(symbols, args.batch_size):
            res = process_chunk(chunk, start_date, end_date,
                                 retry_errors=args.retry_errors,
                                 ticker_company_map=ticker_company_map)
            total_success   += res["success"]
            all_warnings    += res["warnings"]
            all_errors      += res["errors"]
            all_delisted    += res.get("delisted", [])
            total_processed += len(chunk)

    export_error_csv(all_errors)
    print_report(run_date, total_processed, total_success, all_warnings, all_errors, all_delisted)


if __name__ == "__main__":
    main()