import csv
from datetime import datetime, timedelta

def analyze():
    file_path = '/app/working/workspaces/FinCodeur95/duckdb/Features_Pente/knn_backtest.journal.csv'
    events = []

    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                start_date = datetime.strptime(row['entry_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(row['exit_date'], '%Y-%m-%d').date()
                size = float(row['size_eur'])

                # Trade is active from start_date to end_date (inclusive)
                events.append((start_date, size))
                events.append((end_date + timedelta(days=1), -size))

        if not events:
            print("No trades found in the journal.")
            return

        # Sort by date
        events.sort()

        max_cap = 0.0
        current_cap = 0.0
        last_date = None

        for date, change in events:
            current_cap += change
            if current_cap > max_cap:
                max_cap = current_cap

        print(f"Maximum capital engaged: {max_cap:.2f} €")

        rule = 30000.0
        if max_cap > rule:
            print(f"ANOMALY DETECTED: Max capital ({max_cap:.2f} €) exceeds limit ({rule} €)!")
        else:
            print("No anomaly detected regarding maximum capital.")

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    analyze()
