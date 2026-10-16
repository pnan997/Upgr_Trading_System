#!/usr/bin/env python3
"""
Tickers_purge.py — Purge réelle de tickers dans tickers_meta + données OHLCV associées.
Usage : python3 Tickers_purge.py TICK1,TICK2,...,TICKN
"""

import sys
import duckdb
from datetime import datetime

DB_PATH = os.environ["TS_DB_PATH"]

def fetch_tickers_to_purge(conn, requested: list[str]) -> list[dict]:
    """
    Consulte la DB et retourne uniquement les tickers réellement présents.
    Les tickers demandés mais absents sont signalés mais ignorés.
    """
    placeholders = ", ".join(["?" ] * len(requested))
    rows = conn.execute(
        f"""
        SELECT symbol, date_debut_dispo, date_fin_dispo,
               nb_enregistrements, statut, dernier_essai
        FROM tickers_meta
        WHERE symbol IN ({placeholders})
        ORDER BY symbol
        """,
        requested
    ).fetchall()

    return [
        {
            "symbol":            r[0],
            "date_debut":        r[1],
            "date_fin":          r[2],
            "nb_enregistrements": r[3],
            "statut":            r[4],
            "dernier_essai":     r[5],
        }
        for r in rows
    ]


def purge(conn, symbols: list[str]) -> dict:
    """
    Supprime les enregistrements dans tickers_meta (et ohlcv si la table existe).
    Retourne un résumé de ce qui a été supprimé.
    """
    placeholders = ", ".join(["?"] * len(symbols))
    summary = {}

    # Purge table principale
    conn.execute(
        f"DELETE FROM tickers_meta WHERE symbol IN ({placeholders})",
        symbols
    )
    summary["tickers_meta"] = conn.execute("SELECT changes()").fetchone()[0]

    # Purge table OHLCV si elle existe (nom supposé : ohlcv)
    ohlcv_exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'ohlcv'"
    ).fetchone()[0]

    if ohlcv_exists:
        conn.execute(
            f"DELETE FROM ohlcv WHERE symbol IN ({placeholders})",
            symbols
        )
        summary["ohlcv"] = conn.execute("SELECT changes()").fetchone()[0]
    else:
        summary["ohlcv"] = None  # table absente, pas une erreur

    return summary


def main():
    if len(sys.argv) != 2:
        print("Usage : python3 Tickers_purge.py TICK1,TICK2,...,TICKN")
        sys.exit(1)

    requested = [t.strip().upper() for t in sys.argv[1].split(",") if t.strip()]
    if not requested:
        print("Erreur : aucun ticker valide fourni.")
        sys.exit(1)

    conn = duckdb.connect(DB_PATH)

    # --- Consultation DB ---
    found = fetch_tickers_to_purge(conn, requested)
    found_symbols = [r["symbol"] for r in found]
    missing = sorted(set(requested) - set(found_symbols))

    print()
    print("=" * 60)
    print("  PURGE — consultation de la base avant toute action")
    print("=" * 60)

    if missing:
        print(f"\n  ⚠  Tickers ABSENTS de la DB (ignorés) : {', '.join(missing)}")

    if not found:
        print("\n  Aucun ticker à purger. Abandon.")
        conn.close()
        sys.exit(0)

    print(f"\n  Tickers qui SERONT supprimés ({len(found)}) :\n")
    print(f"  {'Symbol':<10} {'Début':>12} {'Fin':>12} {'Enreg.':>8}  {'Statut'}")
    print(f"  {'-'*10} {'-'*12} {'-'*12} {'-'*8}  {'-'*15}")
    for r in found:
        print(
            f"  {r['symbol']:<10} "
            f"{str(r['date_debut']):>12} "
            f"{str(r['date_fin']):>12} "
            f"{str(r['nb_enregistrements'] or 0):>8}  "
            f"{r['statut'] or ''}"
        )

    print()
    print("  ⚡ Cette opération est IRRÉVERSIBLE (sauf restauration backup).")
    print()

    # --- Confirmation ---
    reponse = input("  Confirmer la purge ? [o/N] : ").strip().lower()
    if reponse != "o":
        print("\n  Purge annulée. Aucune donnée modifiée.")
        conn.close()
        sys.exit(0)

    # --- Purge effective ---
    print()
    try:
        summary = purge(conn, found_symbols)
        conn.commit()

        print(f"  ✔  tickers_meta : {summary['tickers_meta']} ligne(s) supprimée(s)")
        if summary["ohlcv"] is not None:
            print(f"  ✔  ohlcv         : {summary['ohlcv']} ligne(s) supprimée(s)")
        else:
            print("  ℹ  Table ohlcv absente — rien à supprimer côté données.")

        print(f"\n  Purge terminée le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        conn.rollback()
        print(f"\n  ✘  Erreur durant la purge — ROLLBACK effectué.")
        print(f"     Détail : {e}")
        sys.exit(1)

    finally:
        conn.close()

    print()


if __name__ == "__main__":
    main()
