"""
Utils/sharpe.py
===============
Calcul du ratio de Sharpe annualisé sur fenêtre glissante 252 jours.

FORMULE
-------
    SR(t) = (mean(r_glissant) − rf_quotidien(t)) × √252
            ─────────────────────────────────────────────
                    std(r_glissant, ddof=1) × √252

Ce qui simplifie en :

    SR(t) = (mean(r_glissant) − rf_quotidien(t)) × √252
            ─────────────────────────────────────────────
                        std(r_glissant, ddof=1) × √252

Note : le √252 se simplifie sur le dénominateur, mais PAS sur le
numérateur car rf_quotidien doit être soustrait *avant* d'annualiser.
Formulation exacte utilisée ici :

    excess_mean = mean(r_glissant) − rf_quotidien   ← en quotidien
    SR(t) = (excess_mean × 252) / (std × √252)
          = excess_mean × √252 / std

TAUX SANS RISQUE
----------------
Stocké dans la table rf_daily (date, taux_annuel).
Le taux annuel est converti en taux quotidien :
    rf_quotidien = taux_annuel / 252

Si une date n'a pas de rf_daily (week-end yfinance, férié) :
    → on prend la dernière valeur disponible (LOCF — Last Observation
      Carried Forward). C'est le comportement "variable d'environnement" :
      la valeur reste celle du dernier jour connu jusqu'à mise à jour.

FENÊTRE GLISSANTE
-----------------
252 jours ouvrés (~1 an boursier). En dessous de 30 jours de données,
le SR n'est pas calculé (NaN → 0.0 dans la table).

TABLES CONCERNÉES
-----------------
    rf_daily      : date (PK) | taux_annuel | source
    ticker_stats  : symbol | date (PK) | ecart_type_an | sharpe_ratio

IMPORT
------
    import sys
    sys.path.insert(0, os.environ["TS_ROOT"])
    from Utils.sharpe import (
        create_tables_if_needed,
        update_rf_today,
        compute_and_store_sharpe,
        backfill_symbol,
    )

VERSION
-------
    1.0 — Mai 2026
"""

import numpy as np
import pandas as pd
import yfinance as yf
import duckdb
import os
from datetime import date, timedelta

# ── Constantes ────────────────────────────────────────────────────────────────
DB_PATH        = os.environ["TS_DB_PATH"]
WINDOW         = 252          # jours ouvrés — fenêtre glissante SR
MIN_PERIODS    = 30           # minimum de jours pour calculer SR
TRADING_DAYS   = 252          # annualisation


# ── DDL — création des tables si elles n'existent pas ────────────────────────

DDL_RF_DAILY = """
CREATE TABLE IF NOT EXISTS rf_daily (
    date        DATE PRIMARY KEY,
    taux_annuel DOUBLE NOT NULL,   -- ex. 0.0425 pour 4.25%
    source      VARCHAR DEFAULT '^IRX'
)
"""

DDL_TICKER_STATS = """
CREATE TABLE IF NOT EXISTS ticker_stats (
    symbol         VARCHAR NOT NULL,
    date           DATE    NOT NULL,
    ecart_type_an  DOUBLE,         -- volatilité annualisée = std × √252
    sharpe_ratio   DOUBLE,         -- SR glissant 252j  (0.0 si données manquantes)
    PRIMARY KEY (symbol, date)
)
"""


def create_tables_if_needed(con):
    """
    Crée rf_daily et ticker_stats si elles n'existent pas encore.
    Idempotent — sans effet si déjà présentes.
    """
    con.execute(DDL_RF_DAILY)
    con.execute(DDL_TICKER_STATS)


# ── Taux sans risque ──────────────────────────────────────────────────────────

def fetch_irx(start: date, end: date) -> pd.DataFrame:
    """
    Télécharge ^IRX (T-Bill 3 mois, taux annuel en %) via yfinance.
    Retourne un DataFrame avec colonnes : date (date), taux_annuel (float).
    Le taux est converti de % → décimal (ex. 5.25 → 0.0525).
    Retourne un DataFrame vide si échec.
    """
    try:
        raw = yf.download(
            '^IRX',
            start=start.strftime('%Y-%m-%d'),
            end=(end + timedelta(days=1)).strftime('%Y-%m-%d'),
            progress=False,
            auto_adjust=True,
        )
        if raw.empty:
            return pd.DataFrame()

        raw = raw.reset_index()[['Date', 'Close']].copy()
        raw.columns = ['date', 'taux_annuel']
        raw['date']        = pd.to_datetime(raw['date']).dt.date
        raw['taux_annuel'] = raw['taux_annuel'] / 100.0   # % → décimal
        raw['source']      = '^IRX'
        return raw.dropna()
    except Exception:
        return pd.DataFrame()


def update_rf_today(con) -> float | None:
    """
    Télécharge le rf du jour (ou du dernier jour disponible) et l'insère
    dans rf_daily. Retourne le taux annuel inséré, ou None si échec.

    Appelé en début de batch delta — c'est le "refresh de la variable
    d'environnement" avant les calculs SR du jour.
    """
    today = date.today()
    # On prend une fenêtre de 5 jours pour absorber les week-ends/fériés
    start = today - timedelta(days=5)

    df_rf = fetch_irx(start, today)
    if df_rf.empty:
        return None

    # On insère toutes les lignes nouvelles (INSERT OR REPLACE)
    for _, row in df_rf.iterrows():
        con.execute("""
            INSERT INTO rf_daily (date, taux_annuel, source)
            VALUES (?, ?, ?)
            ON CONFLICT (date) DO UPDATE SET
                taux_annuel = excluded.taux_annuel,
                source      = excluded.source
        """, [row['date'], row['taux_annuel'], row['source']])

    # Retourne la valeur la plus récente insérée
    last = con.execute("""
        SELECT taux_annuel FROM rf_daily
        ORDER BY date DESC LIMIT 1
    """).fetchone()
    return last[0] if last else None


def get_rf_series(con, date_debut: date, date_fin: date) -> pd.Series:
    """
    Retourne une Series rf quotidien (taux_annuel / 252) indexée par date,
    pour la fenêtre demandée.

    Les jours sans valeur rf sont comblés par LOCF (dernière valeur connue).
    Si aucune valeur rf n'existe du tout → série de zéros (SR = SR brut).
    """
    rows = con.execute("""
        SELECT date, taux_annuel
        FROM rf_daily
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """, [date_debut, date_fin]).fetchdf()

    if rows.empty:
        # Fallback : dernière valeur connue dans toute la table
        last = con.execute("""
            SELECT taux_annuel FROM rf_daily ORDER BY date DESC LIMIT 1
        """).fetchone()
        taux = last[0] / TRADING_DAYS if last else 0.0
        # On retourne une série vide — l'appelant utilisera ce taux fixe
        return pd.Series(dtype=float), taux

    rows['date']        = pd.to_datetime(rows['date']).dt.date
    rows['rf_quotidien'] = rows['taux_annuel'] / TRADING_DAYS
    rows = rows.set_index('date')['rf_quotidien']
    return rows, None


# ── Calcul SR sur une série de rendements ────────────────────────────────────

def compute_sharpe_series(log_returns: pd.Series,
                          rf_series: pd.Series | None,
                          rf_fixe: float = 0.0,
                          window: int = WINDOW,
                          min_periods: int = MIN_PERIODS) -> pd.DataFrame:
    """
    Calcule ecart_type_an et sharpe_ratio pour chaque date,
    sur fenêtre glissante `window` jours.

    Paramètres
    ----------
    log_returns : pd.Series indexée par date (date Python), valeurs float
    rf_series   : pd.Series indexée par date — rf quotidien (taux_annuel/252)
                  Si None, utilise rf_fixe pour toutes les dates.
    rf_fixe     : float — utilisé si rf_series est None ou date absente
    window      : int — taille fenêtre glissante (défaut 252)
    min_periods : int — minimum de jours pour calculer (défaut 30)

    Retourne un DataFrame avec colonnes : date, ecart_type_an, sharpe_ratio
    """
    if log_returns.empty:
        return pd.DataFrame(columns=['date', 'ecart_type_an', 'sharpe_ratio'])

    r = log_returns.copy()
    r.index = pd.to_datetime(r.index)

    results = []
    idx = list(r.index)

    for i, dt in enumerate(idx):
        # Fenêtre glissante : [i-window+1, i]
        start_i = max(0, i - window + 1)
        window_r = r.iloc[start_i:i + 1]

        n = len(window_r)
        if n < min_periods:
            results.append({
                'date':          dt.date(),
                'ecart_type_an': None,
                'sharpe_ratio':  0.0,   # 0.0 = signal "données insuffisantes"
            })
            continue

        mu  = float(window_r.mean())
        std = float(window_r.std(ddof=1))

        # Volatilité annualisée
        vol_an = std * np.sqrt(TRADING_DAYS)

        # rf quotidien pour cette date
        d = dt.date()
        if rf_series is not None and not rf_series.empty and d in rf_series.index:
            rf_q = float(rf_series[d])
        else:
            rf_q = rf_fixe

        # SR annualisé
        if std == 0:
            sr = 0.0
        else:
            # excess_mean quotidien × √252 / (std × √252) = excess_mean / std
            # mais on garde la formule explicite pour lisibilité
            sr = float((mu - rf_q) * np.sqrt(TRADING_DAYS) / vol_an)

        results.append({
            'date':          d,
            'ecart_type_an': round(vol_an, 6),
            'sharpe_ratio':  round(sr, 6),
        })

    return pd.DataFrame(results)


# ── Calcul et stockage pour un ticker ────────────────────────────────────────

def _load_ohlcv_returns(symbol: str, con) -> pd.Series:
    """
    Charge les log-rendements depuis ohlcv_SYMBOL.
    Retourne une Series indexée par date Python, triée.
    """
    table = f"ohlcv_{symbol.replace('-', '_').replace('.', '_')}"
    try:
        df = con.execute(f"""
            WITH base AS (
                SELECT
                    "Date"::DATE                                 AS date,
                    "Close"                                      AS close,
                    LAG("Close") OVER (ORDER BY "Date")          AS close_prev
                FROM {table}
                WHERE "Close" > 0
            )
            SELECT date, LN(close / close_prev) AS log_return
            FROM base
            WHERE close_prev > 0
            ORDER BY date
        """).fetchdf()
    except Exception:
        return pd.Series(dtype=float)

    if df.empty:
        return pd.Series(dtype=float)

    df['date'] = pd.to_datetime(df['date']).dt.date
    return df.set_index('date')['log_return']


def _last_stats_date(symbol: str, con) -> date | None:
    """Retourne la dernière date déjà calculée dans ticker_stats pour ce symbol."""
    row = con.execute("""
        SELECT MAX(date) FROM ticker_stats WHERE symbol = ?
    """, [symbol]).fetchone()
    return row[0] if row and row[0] else None


def compute_and_store_sharpe(symbol: str, con,
                              only_new: bool = True) -> int:
    """
    Calcule et stocke ecart_type_an + sharpe_ratio dans ticker_stats.

    Paramètres
    ----------
    symbol    : str   — ticker
    con       : connexion DuckDB ouverte
    only_new  : bool  — si True, calcule seulement les dates absentes de
                        ticker_stats (mode incrémental pour le batch delta).
                        Si False, recalcule tout (mode backfill).

    Retourne le nombre de lignes insérées/mises à jour.
    """
    create_tables_if_needed(con)

    r = _load_ohlcv_returns(symbol, con)
    if r.empty:
        return 0

    # En mode incrémental : on recalcule depuis (last_date - window) pour
    # que la fenêtre glissante soit correcte, mais on n'insère que les
    # dates nouvelles.
    last_stored = _last_stats_date(symbol, con) if only_new else None

    if only_new and last_stored is not None:
        # Recalcul depuis last_stored - window pour alimenter la fenêtre
        cutoff = pd.to_datetime(last_stored) - pd.Timedelta(days=window_days(WINDOW))
        r_calc = r[r.index >= cutoff.date()]
    else:
        r_calc = r

    if r_calc.empty:
        return 0

    # Récupérer le rf sur la période
    # Old -> d_min = r_calc.index.min()
    # Old -> d_max = r_calc.index.max()
    # Old -> rf_ser, rf_fixe = get_rf_series(con, d_min, d_max)

    d_min = r_calc.index.min()
    d_max = r_calc.index.max()
    rf_ser, rf_fixe = get_rf_series(con, d_min, d_max)

    rf_fixe_safe = rf_fixe if rf_fixe is not None else 0.0
    rf_ser_safe  = rf_ser if (rf_ser is not None and len(rf_ser) > 0) else None

    # Calcul
    # Old -> df_stats = compute_sharpe_series(r_calc, rf_ser if rf_ser is not None else None,
    # Old ->                                 rf_fixe=rf_fixe if rf_fixe else 0.0)

    df_stats = compute_sharpe_series(r_calc, rf_ser_safe, rf_fixe=rf_fixe_safe)
    
    if df_stats.empty:
        return 0

    # Filtrer : n'insérer que les dates > last_stored
    if only_new and last_stored is not None:
        df_stats = df_stats[df_stats['date'] > last_stored]

    if df_stats.empty:
        return 0

    # Remplacement des NaN par 0.0 (signal "données insuffisantes" convenu)
    df_stats['ecart_type_an'] = df_stats['ecart_type_an'].fillna(0.0)
    df_stats['sharpe_ratio']  = df_stats['sharpe_ratio'].fillna(0.0)

    # INSERT bulk
    df_stats['symbol'] = symbol
    con.execute("""
        INSERT INTO ticker_stats (symbol, date, ecart_type_an, sharpe_ratio)
        SELECT symbol, date, ecart_type_an, sharpe_ratio FROM df_stats
        ON CONFLICT (symbol, date) DO UPDATE SET
            ecart_type_an = excluded.ecart_type_an,
            sharpe_ratio  = excluded.sharpe_ratio
    """)

    return len(df_stats)


def window_days(w: int) -> int:
    """Convertit une fenêtre en jours ouvrés en jours calendaires approx."""
    return int(w * 1.45)  # 252 jours ouvrés ≈ 365 jours calendaires


# ── Backfill ──────────────────────────────────────────────────────────────────

def backfill_symbol(symbol: str, con) -> int:
    """
    Recalcule le SR sur tout l'historique disponible pour un symbol.
    Wrapper de compute_and_store_sharpe(only_new=False).
    """
    return compute_and_store_sharpe(symbol, con, only_new=False)