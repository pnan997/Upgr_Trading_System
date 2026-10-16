'''

Isole les erreurs de téléchargement dans un fichier CSV pour analyse ultérieure.

'''
import duckdb
import os
db_path = os.environ["TS_DB_PATH"]
output_path = os.path.join(os.environ["TS_ROOT"], "tickers_errors.csv")

def export_error_tickers():
    conn = duckdb.connect(db_path)
    query = """
        SELECT symbol, statut, dernier_essai, message_erreur 
        FROM tickers_meta
        WHERE statut = 'ERROR'
    """
    
    results = conn.execute(query).fetchdf()
    conn.close()

    if not results.empty:
        results.to_csv(output_path, index=False)
        print(f"Exported {len(results)} error tickers to {output_path}")
    else:
        print("No error tickers found")

if __name__ == '__main__':
    export_error_tickers()