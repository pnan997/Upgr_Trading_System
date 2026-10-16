import yfinance as yf
import pandas as pd

ticker = "^GSPC"
start_date = "2021-01-01"
end_date = "2021-05-31"
output_file = "/Users/pnan9/my_files/GSPC_compl.csv"

try:
    data = yf.download(ticker, start=start_date, end=end_date)
    if data.empty:
        print(f"No data found for {ticker}")
    else:
        # Ensure columns are exactly as requested and handle potential multi-index if necessary
        # yfinance sometimes returns a MultiIndex for columns in newer versions
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        # Check if requested columns exist and filter
        # The user wants Date as a column too. yfinance puts Date in index.
        data = data[required_columns].copy()
        data.reset_index(inplace=True)
        # Rename 'Date' if it shows up differently, but reset_index usually makes it 'Date'
        
        data.to_csv(output_file, index=False)
        print(f"Successfully saved data to {output_file}")
except Exception as e:
    print(f"Error: {e}")
