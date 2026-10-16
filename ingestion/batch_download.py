# +----------------------------------------------------------------------------------------+
# | **ATTENTION** : Bombe atomique de téléchargement de données OHLCV                      |
# | Ce script est conçu pour télécharger des données OHLCV en masse pour un grand nombre   |
# | de tickers. ** IL REMPLACE 5 ANS DE DONNÉES EXISTANTES ** pour chaque ticker.          |
# | Il peut générer un trafic réseau important et entraîner des blocages                   | 
# | de la part des fournisseurs de données. Utilisez-le avec prudence et respectez         |
# | les limites d'utilisation des API.                                                     |
# +----------------------------------------------------------------------------------------+

import duckdb
import yfinance as yf
from datetime import datetime, timedelta
import argparse

db_path = os.environ["TS_DB_PATH"]
error_csv_path = os.path.join(os.environ["TS_ROOT"], "tickers_errors.csv")


def reset_error_statuses(ticker_list):
    """Reset ERROR status à NULL pour les tickers spécifiés."""
    conn = duckdb.connect(db_path)
    if ticker_list:
        placeholders = ','.join(['?'] * len(ticker_list))
        conn.execute(
            f"UPDATE tickers_meta SET statut = NULL WHERE symbol IN ({placeholders})",
            ticker_list
        )
    else:
        conn.execute("UPDATE tickers_meta SET statut = NULL WHERE statut = 'ERROR'")
    conn.close()


def download_ticker_batch(ticker_list, batch_size=20):
    end_date   = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=5 * 365)

    reset_error_statuses(ticker_list)

    try:
        df_all = yf.download(
            tickers=ticker_list,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
            threads=True,
            group_by="ticker"       # MultiIndex : level 0 = ticker, level 1 = field
        )

        success_count = 0
        error_count   = 0
        today         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for ticker in ticker_list:
            conn = duckdb.connect(db_path)
            try:
                # Extraire le sous-DataFrame du ticker
                if len(ticker_list) == 1:
                    # yfinance retourne un DataFrame simple pour un seul ticker
                    df = df_all.copy()
                else:
                    df = df_all[ticker].copy()

                df = df.dropna(how="all")
                df = df.reset_index()   # 'Date' devient une colonne ordinaire

                if df.empty:
                    raise ValueError("No data returned")

                #table_name = f"ohlcv_{ticker.replace('.', '_')}"
                table_name = f"ohlcv_{ticker.replace('.', '_').replace('-', '_')}"
                min_date   = df["Date"].min()
                max_date   = df["Date"].max()
                nb_rows    = len(df)

                # Crée ou remplace la table OHLCV
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.execute(f"""
                    CREATE TABLE {table_name} AS SELECT * FROM df
                """)

                conn.execute(f"""
                    UPDATE tickers_meta
                    SET
                        date_debut_dispo   = ?,
                        date_fin_dispo     = ?,
                        nb_enregistrements = ?,
                        statut             = 'COMPLETED',
                        dernier_essai      = ?,
                        message_erreur     = NULL
                    WHERE symbol = ?
                """, [min_date, max_date, nb_rows, today, ticker])

                success_count += 1

            except Exception as e:
                conn.execute("""
                    UPDATE tickers_meta
                    SET
                        statut         = 'ERROR',
                        dernier_essai  = ?,
                        message_erreur = ?
                    WHERE symbol = ?
                """, [today, str(e), ticker])
                error_count += 1

            finally:
                conn.close()

        # Erreurs remontées par yfinance lui-même
        for ticker, error in yf.shared._ERRORS.items():
            if ticker not in ticker_list:
                continue
            today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn  = duckdb.connect(db_path)
            conn.execute("""
                UPDATE tickers_meta
                SET
                    statut         = 'ERROR',
                    dernier_essai  = ?,
                    message_erreur = ?
                WHERE symbol = ?
            """, [today, str(error), ticker])
            conn.close()
            error_count += 1

        create_error_csv(ticker_list)

        return {
            "total":   len(ticker_list),
            "success": success_count,
            "errors":  error_count,
        }

    except Exception as e:
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn  = duckdb.connect(db_path)
        for ticker in ticker_list:
            conn.execute("""
                UPDATE tickers_meta
                SET
                    statut         = 'ERROR',
                    dernier_essai  = ?,
                    message_erreur = ?
                WHERE symbol = ?
            """, [today, str(e), ticker])
        conn.close()
        create_error_csv(ticker_list)
        return {"total": len(ticker_list), "success": 0, "errors": len(ticker_list)}


def create_error_csv(ticker_list):
    """Exporte les tickers en erreur dans un CSV."""
    conn = duckdb.connect(db_path)
    result = conn.execute("""
        SELECT symbol, statut, dernier_essai, message_erreur
        FROM tickers_meta
        WHERE symbol IN (SELECT UNNEST(?)) AND statut = 'ERROR'
    """, [ticker_list]).fetchdf()
    conn.close()

    if not result.empty:
        result.to_csv(error_csv_path, index=False)
        print(f"Exported {len(result)} error tickers to {error_csv_path}")
    else:
        print("No error tickers found")


def process_batch(batch_size=20):
    conn = duckdb.connect(db_path)
    result = conn.execute("""
        SELECT symbol FROM tickers_meta
        WHERE statut IS NULL OR statut NOT IN ('COMPLETED', 'ERROR')
        LIMIT ?
    """, [batch_size]).fetchall()
    conn.close()

    if not result:
        print("No tickers to process")
        return None

    ticker_list = [row[0] for row in result]
    print(f"Processing : {ticker_list}")
    return download_ticker_batch(ticker_list, batch_size)


def main():
    parser = argparse.ArgumentParser(description="Download OHLCV data in batches")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="Number of tickers per batch (default: 20)")
    args = parser.parse_args()

    batch_results = process_batch(args.batch_size)

    if batch_results:
        print(f"\nBatch Results:")
        print(f"  Total processed : {batch_results['total']}")
        print(f"  Successful      : {batch_results['success']}")
        print(f"  Errors          : {batch_results['errors']}")


if __name__ == "__main__":
    main()