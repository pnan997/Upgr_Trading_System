import pandas as pd
from datetime import timedelta

def analyze():
    file_path = '/app/working/workspaces/FinCodeur95/duckdb/Features_Pente/knn_backtest.journal.csv'

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            print("The journal file is empty.")
            return

        # Convert dates
        df['entry_date'] = pd.to_datetime(df['entry_date'])
        df['exit_date'] = pd.to_datetime(df['exit_date'])
        df = df.sort_values('entry_date')

        # Constants from rules
        CAPITAL_INIT = 30000.0
        TP_PCT = 0.010
        SL_PCT = 0.006
        MAX_TRADE_SIZE = 5000.0
        MIN_CASH_TO_TRADE = 2500.0
        EPSILON = 0.01

        # State tracking
        current_cash = CAPITAL_INIT
        cumulative_deployed = 0.0
        anomalies = []

        for _, row in df.iterrows():
            symbol = row['symbol']
            entry_open = row['entry_open']
            tp_price = row['tp_price']
            exit_price = row['exit_price']
            reason = row['reason']
            size = row['size_eur']

            # 1. Vérification de la règle de taille (avant l'ouverture)
            # La taille doit être min(5000, cash_disponible)
            expected_size = min(MAX_TRADE_SIZE, current_cash)
            if current_cash < MIN_CASH_TO_TRADE:
                expected_size = 0.0

            if abs(size - expected_size) > EPSILON:
                anomalies.append(f"[{row['entry_date'].date()}] {symbol}: Taille incorrecte (Attendu: {expected_size:.2f}, Reçu: {size:.2f} | Cash dispo: {current_cash:.2f})")

            # 2. Vérification du filtre d'entrée (Open >= TP)
            if entry_open >= tp_price:
                anomalies.append(f"[{row['entry_date'].date()}] {symbol}: Filtre d'entrée échoué (Open {entry_open:.2f} >= TP {tp_price:.2f})")

            # 3. Vérification de la sortie (TP/SL)
            if reason == 'TP':
                expected_exit = entry_open * (1 + TP_PCT)
                if abs(exit_price - expected_exit) > EPSILON:
                    anomalies.append(f"[{row['entry_date'].date()}] {symbol}: Erreur de calcul TP (Attendu: {expected_exit:.2f}, Reçu: {exit_price:.2f})")
            elif reason == 'SL':
                expected_exit = entry_open * (1 - SL_PCT)
                if abs(exit_price - expected_exit) > EPSILON:
                    anomalies.append(f"[{row['entry_date'].date()}] {symbol}: Erreur de calcul SL (Attendu: {expected_exit:.2f}, Reçu: {exit_price:.2f})")

            # Mise à jour du cash : on retire la taille au début et on ajoute le PnL à la fin
            current_cash -= size
            current_cash += row['pnl_eur']
            cumulative_deployed += size

        if anomalies:
            print("ANOMALIES DETECTEES :")
            for a in anomalies:
                print(a)
        else:
            print("Pas d'anomalies rencontrées.")

    except Exception as ex:
        import traceback
        print(f"Erreur lors de l'analyse: {ex}")
        traceback.print_exc()

if __name__ == "__main__":
    analyze()
