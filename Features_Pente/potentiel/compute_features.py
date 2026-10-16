import duckdb
import numpy as np
import pandas as pd
import os

### Galop d'essai pour calculer les features de pente et de bruit pour chaque ticker dans la base de données DuckDB.

def calculate_features(symbol, close_prices):
    # Ensure we have enough data
    if len(close_prices) < 60:
        return None

    # Use log prices for regression. Handle potential zeros/negatives just in case.
    # We use a small epsilon to avoid log(0)
    log_close = np.log(np.maximum(close_prices, 1e-9))
    
    # Time index for regression (last 60 points)
    y_60 = log_close[-60:]
    x_60 = np.arange(60)

    # Linear regression on last 60 points
    slope_60, intercept_60 = np.polyfit(x_60, y_60, 1)
    
    # Calculate R^2 for the 60-period trend
    y_pred_60 = slope_60 * x_60 + intercept_60
    residuals_60 = y_60 - y_pred_60
    ss_res_60 = np.sum(residuals_60**2)
    ss_tot_60 = np.sum((y_60 - np.mean(y_60))**2)
    r_squared_60 = 1 - (ss_res_60 / ss_tot_60) if ss_tot_60 != 0 else 0

    # Standard deviation of residuals for noise ratio
    sigma_res_60 = np.std(residuals_60)

    # Short-term trend (last 20 points)
    y_20 = log_close[-20:]
    x_20 = np.arange(20) # relative to the end of the series, but we just need slope
    slope_20, intercept_20 = np.polyfit(x_20, y_20, 1)

    # Feature calculations
    T = slope_60
    Q = r_squared_60
    M = slope_20
    A = slope_20 - slope_60
    epsilon = 1e-9
    N = sigma_res_60 / (abs(slope_60) + epsilon)

    return {
        'symbol': symbol,
        'T': T,
        'Q': Q,
        'M': M,
        'A': A,
        'N': N
    }

def main():
    db_path = os.environ["TS_DB_PATH"]
    output_dir = os.path.join(os.environ["TS_ROOT"], "Features_Pente")
    
    conn = duckdb.connect(db_path)
    
    # Get all tables starting with 'ohlcv_'
    tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'ohlcv_%'").fetchall()
    tickers = [t[0].replace('ohlcv_', '') for t in tables]
    print(f"Found {len(tickers)} tickers.")

    results = []
    for symbol in tickers:
        try:
            # Fetch close prices. Quote the table name to handle special characters like ^
            table_name = f'ohlcv_{symbol}'
            df = conn.execute(f'SELECT * FROM "{table_name}" ORDER BY date ASC').df()
            if df.empty:
                continue
            
            # Normalize column names to lowercase for easier access
            df.columns = [c.lower() for c in df.columns]
            close_prices = df['close'].values
            feat = calculate_features(symbol, close_prices)
            if feat:
                results.append(feat)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    # Create DataFrame and save
    res_df = pd.DataFrame(results)
    os.makedirs(output_dir, exist_ok=True)
    res_df.to_csv(f"{output_dir}/features_pente.csv", index=False)
    print(f"Saved {len(res_df)} rows to {output_dir}/features_pente.csv")

if __name__ == "__main__":
    main()
