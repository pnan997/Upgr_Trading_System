import duckdb
import pandas as pd
import os

def main():
    db_path = os.environ["TS_DB_PATH"]
    project_dir = os.path.join(os.environ["TS_ROOT"], "Features_Pente_Walk_Forward")
    input_path  = os.environ.get("WF_ENRICH_IN",  f'{project_dir}/test_features_with_predictions.csv')
    output_path = os.environ.get("WF_ENRICH_OUT", f'{project_dir}/test_features_with_predictions_ohlcv.csv')

    print("--- Chargement des prédictions ---")
    df_preds = pd.read_csv(input_path, parse_dates=['date'])
    symbols = df_preds['symbol'].unique()
    print(f"{len(df_preds)} lignes, {len(symbols)} symboles\n")

    conn = duckdb.connect(db_path, read_only=True)

    print("--- Enrichissement OHLCV (jour J) par symbole ---")
    enriched_parts = []
    n_errors = 0
    n_missing_total = 0

    for symbol in symbols:
        sub = df_preds[df_preds['symbol'] == symbol]
        table_name = f'ohlcv_{symbol}'
        try:
            ohlcv = conn.execute(
                f'SELECT "Date"::DATE AS date, "Open", "High", "Low", "Close", "Volume" '
                f'FROM "{table_name}"'
            ).df()
        except Exception as e:
            print(f"  [ERREUR] {symbol}: table introuvable ou invalide ({e})")
            n_errors += 1
            continue

        merged = sub.merge(ohlcv, on='date', how='left')
        n_missing = int(merged['Close'].isna().sum())
        if n_missing:
            print(f"  [WARNING] {symbol}: {n_missing}/{len(merged)} ligne(s) sans OHLCV correspondant (date absente de la table)")
            n_missing_total += n_missing

        enriched_parts.append(merged)

    print("\n--- Fusion et sauvegarde ---")
    result = pd.concat(enriched_parts, ignore_index=True)

    os.makedirs(project_dir, exist_ok=True)
    result.to_csv(output_path, index=False)

    print(f"Symboles traités : {len(symbols) - n_errors}/{len(symbols)} ({n_errors} erreur(s) de table)")
    print(f"Lignes en sortie : {len(result)} (dont {n_missing_total} sans OHLCV apparié)")
    print(f"Sauvegardé : {output_path}")

if __name__ == '__main__':
    main()
