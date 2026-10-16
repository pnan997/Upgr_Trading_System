"""
Utils/returns.py — Module rendements logarithmiques
Version 2.0 — Mai 2026

Nouvelles métriques v2 : p33, p67, ratio_terciles, mode_approx,
delta_moy_med, position_zero
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import gaussian_kde
import duckdb


# ─────────────────────────────────────────────
# Connexion par défaut
# ─────────────────────────────────────────────
DB_PATH = os.environ["TS_DB_PATH"]


def _get_con(con=None):
    if con is not None:
        return con, False
    return duckdb.connect(DB_PATH, read_only=True), True


# ─────────────────────────────────────────────
# get_returns
# ─────────────────────────────────────────────
def get_returns(symbol, date_debut=None, date_fin=None, con=None):
    """
    Retourne un DataFrame avec colonnes :
        date, close, close_prev, log_return

    Les tables OHLCV ont des colonnes en majuscules (Date, Open, High,
    Low, Close, Volume). La fonction normalise tout en minuscules à la
    sortie.

    Filtres appliqués : Close > 0 ET close_prev > 0.
    """
    con_local, owns = _get_con(con)
    table = f'ohlcv_{symbol.replace("-", "_")}'

    try:
        query = f"""
            WITH base AS (
                SELECT
                    "Date"                              AS date,
                    "Close"                             AS close,
                    LAG("Close") OVER (ORDER BY "Date") AS close_prev
                FROM {table}
                WHERE "Close" > 0
            )
            SELECT
                date,
                close,
                close_prev,
                LN(close / close_prev) AS log_return
            FROM base
            WHERE close_prev > 0
        """

        if date_debut:
            query = query.rstrip() + f"\n  AND date >= '{date_debut}'"
        if date_fin:
            query = query.rstrip() + f"\n  AND date <= '{date_fin}'"

        query += "\nORDER BY date"

        df = con_local.execute(query).df()
        return df

    finally:
        if owns:
            con_local.close()


# ─────────────────────────────────────────────
# _mode_from_kde  (interne)
# ─────────────────────────────────────────────
def _mode_from_kde(values, bandwidth='scott'):
    """
    Estime le mode via KDE scipy.
    Retourne (mode_x, x_grid, kde_values) pour réutilisation graphique.
    """
    kde = gaussian_kde(values, bw_method=bandwidth)
    x_grid = np.linspace(values.min(), values.max(), 1000)
    kde_vals = kde(x_grid)
    mode_x = x_grid[np.argmax(kde_vals)]
    return mode_x, x_grid, kde_vals


# ─────────────────────────────────────────────
# get_distribution_stats
# ─────────────────────────────────────────────
def get_distribution_stats(symbol, date_debut=None, date_fin=None, con=None):
    """
    Retourne un dictionnaire de statistiques descriptives sur les
    rendements logarithmiques journaliers.

    Clés v1 (inchangées) :
        symbol, date_debut, date_fin, n,
        mean, std, vol_annuelle,
        skewness, kurtosis, jarque_bera_p,
        percentile_5, percentile_95, min, max

    Clés v2 (nouvelles) :
        p33, p67,            — terciles
        ratio_terciles,      — (max - P67) / (P33 - min)  > 1 = queue droite plus large
        mode_approx,         — x au pic de la KDE
        delta_moy_med,       — mean - median  (en %, deux décimales)
        position_zero        — 'gauche' | 'centrale' | 'droite'
    """
    df = get_returns(symbol, date_debut=date_debut, date_fin=date_fin, con=con)

    if df.empty or len(df) < 20:
        return {'symbol': symbol, 'error': 'Données insuffisantes'}

    r = df['log_return'].dropna().values

    # — stats de base —
    mean      = float(np.mean(r))
    std       = float(np.std(r, ddof=1))
    skewness  = float(stats.skew(r))
    kurtosis  = float(stats.kurtosis(r))   # excess kurtosis
    jb_stat, jb_p = stats.jarque_bera(r)

    p5,  p33, p67, p95 = np.percentile(r, [5, 33, 67, 95])
    rmin, rmax = float(r.min()), float(r.max())

    # — ratio terciles —
    largeur_droite = rmax - float(p67)
    largeur_gauche = float(p33) - rmin
    ratio_terciles = (largeur_droite / largeur_gauche) if largeur_gauche != 0 else np.nan

    # — mode KDE —
    mode_approx, _, _ = _mode_from_kde(r)

    # — delta moyenne/médiane en % —
    mediane       = float(np.median(r))
    delta_moy_med = float((mean - mediane) * 100)

    # — position du zéro —
    if 0 < float(p33):
        position_zero = 'gauche'
    elif 0 > float(p67):
        position_zero = 'droite'
    else:
        position_zero = 'centrale'

    # — fenêtre effective —
    d_debut = str(df['date'].min())[:10]
    d_fin   = str(df['date'].max())[:10]

    return {
        # identification
        'symbol':          symbol,
        'date_debut':      d_debut,
        'date_fin':        d_fin,
        'n':               int(len(r)),
        # moments
        'mean':            round(mean,     6),
        'std':             round(std,      6),
        'vol_annuelle':    round(std * np.sqrt(252), 4),
        'skewness':        round(skewness, 4),
        'kurtosis':        round(kurtosis, 4),
        'jarque_bera_p':   round(float(jb_p), 6),
        # percentiles v1
        'percentile_5':    round(float(p5),  6),
        'percentile_95':   round(float(p95), 6),
        'min':             round(rmin, 6),
        'max':             round(rmax, 6),
        # v2 — terciles
        'p33':             round(float(p33), 6),
        'p67':             round(float(p67), 6),
        'ratio_terciles':  round(ratio_terciles, 4),
        # v2 — mode / médiane
        'mode_approx':     round(float(mode_approx), 6),
        'delta_moy_med':   round(delta_moy_med, 4),   # en %
        'position_zero':   position_zero,
    }


# ─────────────────────────────────────────────
# compare_windows
# ─────────────────────────────────────────────
def compare_windows(symbol, windows, con=None):
    """
    Compare les stats sur plusieurs fenêtres temporelles.

    windows = liste de tuples (label, date_debut, date_fin)
    Retourne un DataFrame avec une ligne par fenêtre.
    """
    rows = []
    for label, d_debut, d_fin in windows:
        s = get_distribution_stats(symbol, date_debut=d_debut,
                                   date_fin=d_fin, con=con)
        s['fenetre'] = label
        rows.append(s)

    df = pd.DataFrame(rows)
    if 'fenetre' in df.columns:
        cols = ['fenetre'] + [c for c in df.columns if c != 'fenetre']
        df = df[cols]
    return df