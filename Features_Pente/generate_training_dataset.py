import duckdb
import numpy as np
import pandas as pd
import os

def compute_all(symbol, df):
    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    prices = df['close'].values
    dates = df['date'].values
    n = len(prices)

    T = np.full(n, np.nan)
    Q = np.full(n, np.nan)
    M = np.full(n, np.nan)
    A = np.full(n, np.nan)
    N = np.full(n, np.nan)
    Y = np.full(n, np.nan)

    epsilon = 1e-9

    # We need at least 60 days for features and we want to look up to 10 days ahead
    for i in range(59, n):
        # --- Feature Calculation (Window [i-59, i]) ---
        y_60 = np.log(np.maximum(prices[i-59 : i+1], epsilon))
        x_60 = np.arange(60)

        slope_60, intercept_60 = np.polyfit(x_60, y_60, 1)

        # R^2 calculation
        y_pred_60 = slope_60 * x_60 + intercept_60
        ss_res_60 = np.sum((y_60 - y_pred_60)**2)
        ss_tot_60 = np.sum((y_60 - np.mean(y_60))**2)
        r_squared_60 = 1 - (ss_res_60 / ss_tot_60) if ss_tot_60 != 0 else 0

        # Short term trend (last 20 points)
        y_20 = np.log(np.maximum(prices[i-19 : i+1], epsilon))
        x_20 = np.arange(20)
        slope_20, _ = np.polyfit(x_20, y_20, 1)

        # Store features
        T[i] = slope_60
        Q[i] = r_squared_60
        M[i] = slope_20
        A[i] = slope_20 - slope_60
        sigma_res_60 = np.std(y_60 - y_pred_60)
        N[i] = sigma_res_60 / (abs(slope_60) + epsilon)

        # --- Target Calculation (Window [i+1, i+10]) ---
        if i < n - 10:
            future_prices = prices[i+1 : i+11]
            if np.any(future_prices / prices[i] >= 1.01):
                Y[i] = 1
            else:
                Y[i] = 0

    res_df = pd.DataFrame({
        'date': dates,
        'symbol': symbol,
        'T': T,
        'Q': Q,
        'M': M,
        'A': A,
        'N': N,
        'target': Y
    })

    return res_df.dropna()

def main():
    db_path = os.environ["TS_DB_PATH"]
    output_dir = os.path.join(os.environ["TS_ROOT"], "Features_Pente")
    os.makedirs(output_dir, exist_ok=True)

    conn = duckdb.connect(db_path)
    tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'ohlcv_%'").fetchall()
    tickers = [t[0].replace('ohlcv_', '') for t in tables]

    all_dfs = []
    for symbol in tickers:
        try:
            table_name = f'ohlcv_{symbol}'
            df = conn.execute(f'SELECT * FROM "{table_name}" ORDER BY date ASC').df()
            if df.empty or len(df) < 71: # Need at least 60 + 10 days
                continue

            df.columns = [c.lower() for c in df.columns]
            ticker_df = compute_all(symbol, df)
            all_dfs.append(ticker_df)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    if not all_dfs:
        print("No data found.")
        return

    full_df = pd.concat(all_dfs, ignore_index=True)
    full_df['date'] = pd.to_datetime(full_df['date'])

    # Split Logic (Strict Option A)
    split_date = full_df['date'].quantile(0.75)

    # Gap of 10 days to ensure no overlap between Train and Test
    train_mask = full_df['date'] <= (split_date - pd.Timedelta(days=10))
    test_mask = full_df['date'] >= split_date

    train_df = full_df[train_mask]
    test_df = full_df[test_mask]

    print(f"Total rows: {len(full_df)}")
    print(f"Train rows: {len(train_df)} (up to {train_df['date'].max()})")
    print(f"Test rows: {len(test_df)} (from {test_df['date'].min()})")

    train_df.to_csv(f"{output_dir}/train_features.csv", index=False)
    test_df.to_csv(f"{output_dir}/test_features.csv", index=False)
    print(f"Saved to {output_dir}/")

if __name__ == "__main__":
    main()