#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
knn_backtest.py
===============

Backtest de la strategie kNN_SMT a partir des predictions journalieres.

Configuration
-------------
Tous les parametres metier sont dans knn_backtest_config.json (meme dossier).

Regles metier (contexte3.md)
-----------------------------
- capital_engage  : budget journalier — existing_exposure + daily_deployed <= capital_engage
- Entree          : Open du LENDEMAIN du signal (prediction=1)
- Sortie intra    : si |Low-Open| > |High-Open| -> SL d'abord, sinon TP
- Filtre entree   : si Open(D+1) >= Close(D)*(1+tp_pct) -> on n'achete pas
- Same-day        : verifie immediatement le jour de l'entree sur H/L du jour
- Gap-down        : si Open[Dx] <= SL_price sur position multi-jours -> execution a Open
- Gap-up          : si Open[Dx] >= TP_price sur position multi-jours -> execution a Open
- Fin de test     : positions encore ouvertes annulees au prix d'achat (PnL=0)

Ordre d'execution par jour
---------------------------
  (A) liquid_cash += pending_cash  (cash des clotures de la veille)
  (C) Nouvelles entrees            (budget = CAPITAL_ENGAGE - existing_exposure - daily_deployed)
  (B) Cloture des positions existantes (gap-down inclus)
  (D) Instantane equite

Corrections v3 (2026-06-15)
----------------------------
1. Ordre C avant B : l'exposition pre-jour est figee avant toute entree.
   Les sorties du jour ne liberent pas de budget pour les entrees du meme jour.
2. daily_deployed : anti-recyclage same-day. Les trades fermes le meme jour
   comptent dans le budget journalier et ne liberent pas de room pour d'autres.
3. Gap-down : si Open[Dx] <= SL -> execution au prix d'Open (slippage de gap),
   uniquement sur positions multi-jours.
4. Drawdown : redefinition en perte max journaliere (max |daily_pnl negatif|).
   Le max peak-to-trough cumule est conserve sous max_drawdown_cumul_eur.

Corrections v4 (2026-06-16)
----------------------------
1. Gap-up : symetrique du gap-down (point 3, v3). Si Open[Dx] >= TP_price sur
   une position multi-jours, l'objectif est atteint pendant la nuit -> execution
   au prix d'Open (slippage favorable). Raison journal : TP_GAP.

Sorties (dans Features_Pente/)
------------------------------
- knn_backtest.log / .journal.csv / .summary.csv / .equity.csv
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import os

# ===========================================================================
# Chemins
# ===========================================================================
CSV_PATH     = Path(os.path.join(os.environ["TS_ROOT"], "Features_Pente_Walk_Forward",
                    "test_features_with_predictions_ohlcv.csv"))
OUT_DIR      = CSV_PATH.parent
LOG_PATH     = OUT_DIR / "knn_backtest.log"
JOURNAL_PATH = OUT_DIR / "knn_backtest.journal.csv"
SUMMARY_PATH = OUT_DIR / "knn_backtest.summary.csv"
EQUITY_PATH  = OUT_DIR / "knn_backtest.equity.csv"
CONFIG_PATH  = Path(__file__).parent / "knn_backtest_config.json"

# ===========================================================================
# Logging
# ===========================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("knn_backtest")


# ===========================================================================
# Configuration
# ===========================================================================
def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config introuvable : {path}")
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    required = {"capital_initial", "capital_engage", "tp_pct", "sl_pct",
                "plafond_lot", "seuil_minimal", "seed"}
    missing = required - {k for k in cfg if not k.startswith("_")}
    if missing:
        raise KeyError(f"Cles manquantes : {missing}")
    return cfg


# ===========================================================================
# Chargement des donnees
# ===========================================================================
def load_data(csv_path: Path) -> pd.DataFrame:
    log.info(f"Chargement : {csv_path}")
    df = pd.read_csv(csv_path, dtype={"symbol": "string"}, parse_dates=["date"])
    required = {"date", "symbol", "prediction", "Open", "High", "Low", "Close"}
    missing = required - set(df.columns)
    if missing:
        log.error(f"Colonnes manquantes : {missing}")
        sys.exit(2)
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    log.info(f"  {len(df):,} lignes | {df['date'].nunique()} dates | "
             f"{df['symbol'].nunique()} symbols | "
             f"{df['date'].min().date()} -> {df['date'].max().date()}")
    return df


# ===========================================================================
# Sortie intra-journaliere
# ===========================================================================
def resolve_exit(
    day_open: float, day_high: float, day_low: float,
    tp_price: float, sl_price: float,
) -> Tuple[Optional[float], str]:
    """
    Regle d'ordre : |Low-Open| > |High-Open| -> SL d'abord, sinon TP.
    Retourne (prix_sortie, raison) ou (None, "hold").
    """
    if any(pd.isna(x) for x in (day_open, day_high, day_low)):
        return None, "no_data"

    dist_down = abs(day_low  - day_open)
    dist_up   = abs(day_high - day_open)

    if dist_down > dist_up:
        if day_low  <= sl_price: return sl_price, "SL"
        if day_high >= tp_price: return tp_price, "TP"
    else:
        if day_high >= tp_price: return tp_price, "TP"
        if day_low  <= sl_price: return sl_price, "SL"

    return None, "hold"


# ===========================================================================
# Simulation
# ===========================================================================
def run_backtest(
    df: pd.DataFrame, cfg: dict
) -> Tuple[pd.DataFrame, pd.DataFrame, List[dict]]:

    CAPITAL_INIT   = float(cfg["capital_initial"])
    CAPITAL_ENGAGE = float(cfg["capital_engage"])
    TP_PCT         = float(cfg["tp_pct"])
    SL_PCT         = float(cfg["sl_pct"])
    PLAFOND_LOT    = float(cfg["plafond_lot"])
    SEUIL_MINIMAL  = float(cfg["seuil_minimal"])
    SEED           = int(cfg["seed"])

    # Indexation
    log.info("Indexation ...")
    ohlc_index: Dict = {}
    pred_index: Dict = {}
    for d, sub in df.groupby("date", sort=True):
        ohlc_index[d] = {r["symbol"]: {"Open": r["Open"], "High": r["High"],
                                        "Low": r["Low"],  "Close": r["Close"]}
                         for _, r in sub.iterrows()}
        pred_index[d] = dict(zip(sub["symbol"], sub["prediction"]))
    all_dates = sorted(ohlc_index.keys())
    log.info(f"  {len(all_dates)} dates")

    # Etat
    open_positions: Dict[str, dict] = {}
    liquid_cash  = CAPITAL_INIT
    pending_cash = 0.0
    cum_pnl      = 0.0
    journal: List[dict]     = []
    equity_rows: List[dict] = []

    # Boucle
    for day_idx, day in enumerate(all_dates):

        # (A) Liquidite : cash des clotures de la veille
        liquid_cash  = round(liquid_cash + pending_cash, 2)
        pending_cash = 0.0
        day_ohlc     = ohlc_index.get(day, {})

        # Exposition figee AVANT toute entree ou sortie du jour
        existing_exposure = round(sum(p["size"] for p in open_positions.values()), 2)

        # --------------------------------------------------------------
        # (C) Nouvelles entrees : signaux de D-1, entree a Open(D)
        #
        # Budget journalier :
        #   room = CAPITAL_ENGAGE - existing_exposure - daily_deployed
        #   daily_deployed s'accumule et NE SE RECYCLE PAS dans la journee :
        #   une sortie same-day ne libere pas de budget pour un autre trade.
        # --------------------------------------------------------------
        if 0 < day_idx < len(all_dates) - 1:
            prev_day      = all_dates[day_idx - 1]
            candidates    = [s for s, p in pred_index.get(prev_day, {}).items()
                             if p == 1.0]

            if candidates:
                prev_day_ohlc  = ohlc_index.get(prev_day, {})
                daily_deployed = 0.0

                day_rng = np.random.default_rng(SEED + day_idx)
                day_rng.shuffle(candidates)

                missed = 0
                for sym in candidates:
                    if sym in open_positions:
                        continue

                    room_engage = max(0.0, CAPITAL_ENGAGE - existing_exposure - daily_deployed)
                    T = round(min(PLAFOND_LOT, liquid_cash, room_engage), 2)
                    if T < SEUIL_MINIMAL:
                        break

                    ohlc = day_ohlc.get(sym)
                    if ohlc is None:
                        missed += 1; continue

                    price = ohlc["Open"]
                    if pd.isna(price) or price <= 0:
                        missed += 1; continue
                    price = round(float(price), 2)

                    # Filtre : Open(D) >= TP sur Close(D-1) ?
                    prev_ohlc = prev_day_ohlc.get(sym)
                    if prev_ohlc is not None:
                        cp = prev_ohlc["Close"]
                        if not pd.isna(cp) and cp > 0:
                            if price >= round(float(cp) * (1.0 + TP_PCT), 2):
                                missed += 1; continue

                    tp_price = round(price * (1.0 + TP_PCT), 2)
                    sl_price = round(price * (1.0 - SL_PCT), 2)

                    N = int(T // price)
                    if N <= 0:
                        missed += 1; continue
                    S = round(N * price, 2)
                    if S > liquid_cash:
                        S = round(liquid_cash, 2)
                    if S < SEUIL_MINIMAL:
                        missed += 1; continue

                    liquid_cash    = round(liquid_cash - S, 2)
                    daily_deployed = round(daily_deployed + S, 2)

                    # Check same-day
                    ep_sd, rs_sd = resolve_exit(price, ohlc["High"], ohlc["Low"],
                                                tp_price, sl_price)
                    if rs_sd not in ("hold", "no_data") and ep_sd is not None:
                        ep_sd = round(ep_sd, 2)
                        pnl   = round(S * (ep_sd / price - 1.0), 2)
                        pending_cash += S + pnl
                        cum_pnl = round(cum_pnl + pnl, 2)
                        journal.append({
                            "symbol": sym, "entry_date": day.date().isoformat(),
                            "entry_price": price, "size_eur": S,
                            "sl_price": sl_price, "tp_price": tp_price,
                            "exit_date": day.date().isoformat(),
                            "exit_price": ep_sd, "reason": rs_sd,
                            "pnl_eur": pnl,
                            "pnl_pct": round((ep_sd / price - 1.0) * 100, 4),
                            "holding_days": 0,
                        })
                    else:
                        open_positions[sym] = {
                            "entry_date": day, "size": S,
                            "entry_price": price,
                            "sl_price": sl_price, "tp_price": tp_price,
                        }

                if day_idx % 20 == 0:
                    log.info(
                        f"  j{day_idx+1:>3}/{len(all_dates)} {day.date()} | "
                        f"pos={len(open_positions):>2} "
                        f"cash={liquid_cash:>10,.2f} "
                        f"exp0={existing_exposure:>8,.2f} "
                        f"dep={daily_deployed:>8,.2f} "
                        f"cand={len(candidates):>4} miss={missed}"
                    )

        # --------------------------------------------------------------
        # (B) Cloture des positions existantes (jours PRECEDENTS uniquement)
        #
        # Gap-down : si Open[D] <= SL_price -> execution a Open (slippage).
        # Les positions ouvertes AUJOURD'HUI (entry_date == day) sont ignorees
        # ici : leur check same-day a deja ete fait dans (C).
        # --------------------------------------------------------------
        if open_positions:
            to_close: List[str] = []
            for sym, pos in open_positions.items():

                if pos["entry_date"].date() == day.date():
                    continue  # entree aujourd'hui -> pas de re-check

                ohlc = day_ohlc.get(sym)
                if ohlc is None:
                    continue

                open_val = float(ohlc["Open"]) if not pd.isna(ohlc["Open"]) else None

                if open_val is not None and open_val >= pos["tp_price"]:
                    # Gap-up : objectif atteint pendant la nuit (slippage favorable)
                    exit_price = round(open_val, 2)
                    reason     = "TP_GAP"
                elif open_val is not None and open_val <= pos["sl_price"]:
                    # Gap-down : slippage, on execute a l'ouverture
                    exit_price = round(open_val, 2)
                    reason     = "SL_GAP"
                else:
                    exit_price, reason = resolve_exit(
                        ohlc["Open"], ohlc["High"], ohlc["Low"],
                        pos["tp_price"], pos["sl_price"],
                    )

                if reason in ("no_data", "hold"):
                    continue

                exit_price = round(exit_price, 2)
                pnl = round(pos["size"] * (exit_price / pos["entry_price"] - 1.0), 2)
                pending_cash += pos["size"] + pnl
                cum_pnl = round(cum_pnl + pnl, 2)

                journal.append({
                    "symbol": sym,
                    "entry_date": pos["entry_date"].date().isoformat(),
                    "entry_price": pos["entry_price"],
                    "size_eur": pos["size"],
                    "sl_price": pos["sl_price"], "tp_price": pos["tp_price"],
                    "exit_date": day.date().isoformat(),
                    "exit_price": exit_price, "reason": reason,
                    "pnl_eur": pnl,
                    "pnl_pct": round((exit_price / pos["entry_price"] - 1.0) * 100, 4),
                    "holding_days": (day - pos["entry_date"]).days,
                })
                to_close.append(sym)

            for s in to_close:
                del open_positions[s]

        # --------------------------------------------------------------
        # (D) Instantane equite fin de journee
        # --------------------------------------------------------------
        mkt_val = 0.0
        for sym, pos in open_positions.items():
            o = day_ohlc.get(sym)
            if o is not None and not pd.isna(o["Close"]):
                mkt_val += pos["size"] * float(o["Close"]) / pos["entry_price"]
            else:
                mkt_val += pos["size"]
        mkt_val  = round(mkt_val, 2)
        exposure = round(sum(p["size"] for p in open_positions.values()), 2)

        equity_rows.append({
            "date":         day.date().isoformat(),
            "total_equity": round(liquid_cash + pending_cash + mkt_val, 2),  # pending = sorties du jour non encore regles
            "cash":         liquid_cash,
            "market_value": mkt_val,
            "pending_cash": pending_cash,
            "exposure":     exposure,
            "n_positions":  len(open_positions),
        })

    open_at_end = list(open_positions.values())
    equity_df   = pd.DataFrame(equity_rows)
    if not equity_df.empty:
        equity_df["daily_pnl"] = equity_df["total_equity"].diff().fillna(0.0)

    return equity_df, pd.DataFrame(journal), open_at_end


# ===========================================================================
# Metriques
# ===========================================================================
def write_summary(equity_df, journal_df, open_at_end, cfg):
    metrics = {}
    CAPITAL_INIT = float(cfg["capital_initial"])
    final_equity = equity_df["total_equity"].iloc[-1] if not equity_df.empty else CAPITAL_INIT

    metrics["capital_initial"]    = CAPITAL_INIT
    metrics["capital_engage_max"] = float(cfg["capital_engage"])
    metrics["capital_final"]      = final_equity
    metrics["pnl_total"]          = final_equity - CAPITAL_INIT
    metrics["retour_pct"]         = metrics["pnl_total"] / CAPITAL_INIT * 100.0

    n = len(journal_df)
    metrics["n_trades"] = n

    if n > 0:
        wins   = journal_df[journal_df["pnl_eur"] > 0]
        losses = journal_df[journal_df["pnl_eur"] <= 0]
        sg = wins["pnl_eur"].sum()   if len(wins)   else 0.0
        sl = losses["pnl_eur"].sum() if len(losses) else 0.0
        metrics["n_wins"]              = len(wins)
        metrics["n_losses"]            = len(losses)
        metrics["win_rate_pct"]        = 100.0 * len(wins) / n
        metrics["gain_moyen"]          = wins["pnl_eur"].mean()   if len(wins)   else 0.0
        metrics["perte_moyenne"]       = losses["pnl_eur"].mean() if len(losses) else 0.0
        metrics["ratio_gain_perte"]    = sg / abs(sl) if sl != 0 else float("inf")
        metrics["esperance_par_trade"] = (
            metrics["win_rate_pct"] / 100.0 * metrics["gain_moyen"]
            + (1.0 - metrics["win_rate_pct"] / 100.0) * metrics["perte_moyenne"]
        )
        metrics["duree_moyenne_jours"] = journal_df["holding_days"].mean()
        metrics["duree_mediane_jours"] = journal_df["holding_days"].median()
        metrics["duree_max_jours"]     = journal_df["holding_days"].max()
        # Decomposition same-day / multi-day
        sd = journal_df[journal_df["holding_days"] == 0]
        md = journal_df[journal_df["holding_days"] >  0]
        metrics["n_same_day"]  = len(sd)
        metrics["n_multi_day"] = len(md)
        metrics["pnl_same_day"]  = sd["pnl_eur"].sum() if len(sd) else 0.0
        metrics["pnl_multi_day"] = md["pnl_eur"].sum() if len(md) else 0.0
        sl_gap = journal_df[journal_df["reason"] == "SL_GAP"]
        metrics["n_sl_gap"]     = len(sl_gap)
        metrics["pnl_sl_gap"]   = sl_gap["pnl_eur"].sum() if len(sl_gap) else 0.0
        tp_gap = journal_df[journal_df["reason"] == "TP_GAP"]
        metrics["n_tp_gap"]     = len(tp_gap)
        metrics["pnl_tp_gap"]   = tp_gap["pnl_eur"].sum() if len(tp_gap) else 0.0
    else:
        for k in ("n_wins","n_losses","win_rate_pct","gain_moyen","perte_moyenne",
                  "ratio_gain_perte","esperance_par_trade","duree_moyenne_jours",
                  "duree_mediane_jours","duree_max_jours","n_same_day","n_multi_day",
                  "pnl_same_day","pnl_multi_day","n_sl_gap","pnl_sl_gap",
                  "n_tp_gap","pnl_tp_gap"):
            metrics[k] = 0.0

    if not equity_df.empty:
        ev = equity_df["total_equity"].values
        dp = equity_df["daily_pnl"].values

        # Drawdown = perte max sur UNE journee (definition operationnelle)
        neg = dp[dp < 0]
        metrics["max_perte_journaliere_eur"] = round(abs(neg.min()), 2) if len(neg) else 0.0

        # Peak-to-trough cumule (reference standard, pour information)
        running_max = np.maximum.accumulate(ev)
        metrics["max_drawdown_cumul_eur"] = round(float((running_max - ev).max()), 2)
    else:
        metrics["max_perte_journaliere_eur"] = 0.0
        metrics["max_drawdown_cumul_eur"]    = 0.0

    metrics["n_positions_ouvertes_fin"]   = len(open_at_end)
    metrics["pnl_positions_ouvertes_fin"] = 0.0
    metrics["seed"]        = cfg["seed"]
    metrics["tp_pct"]      = float(cfg["tp_pct"]) * 100.0
    metrics["sl_pct"]      = float(cfg["sl_pct"]) * 100.0
    metrics["plafond_lot"] = cfg["plafond_lot"]
    metrics["seuil_min"]   = cfg["seuil_minimal"]

    pd.DataFrame([metrics]).to_csv(SUMMARY_PATH, index=False, encoding="utf-8")
    log.info(f"Summary -> {SUMMARY_PATH}")
    log.info("=== Metriques cles ===")
    for k, v in metrics.items():
        if isinstance(v, float):
            log.info(f"  {k:<36s} = {v:>14,.4f}")
        else:
            log.info(f"  {k:<36s} = {v}")


# ===========================================================================
# Main
# ===========================================================================
def main() -> int:
    t0 = time.time()
    log.info("=== knn_backtest START ===")
    cfg = load_config(CONFIG_PATH)
    log.info(f"  capital_initial  = {cfg['capital_initial']:>10,.2f}")
    log.info(f"  capital_engage   = {cfg['capital_engage']:>10,.2f}")
    log.info(f"  TP={float(cfg['tp_pct'])*100:.3f}%  SL={float(cfg['sl_pct'])*100:.3f}%  "
             f"lot={cfg['plafond_lot']:.0f}  min={cfg['seuil_minimal']:.0f}  seed={cfg['seed']}")

    df = load_data(CSV_PATH)
    equity_df, journal_df, open_at_end = run_backtest(df, cfg)

    log.info(f"Trades : {len(journal_df):,} | Positions en cours fin : {len(open_at_end)}")
    equity_df.to_csv(EQUITY_PATH,   index=False, encoding="utf-8")
    journal_df.to_csv(JOURNAL_PATH, index=False, encoding="utf-8")
    write_summary(equity_df, journal_df, open_at_end, cfg)

    log.info(f"=== DONE en {time.time()-t0:.1f} s ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
