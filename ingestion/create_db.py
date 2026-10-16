#!/usr/bin/env python3
"""

### ** ATTENTION ** : BOMBE ATOMIQUE ! Ce script supprime la base de données existante et la recrée.

Script d'initialisation de la base DuckDB pour le stockage OHLCV
Crée la table tickers_meta et initialise tous les tickers en PENDING
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
import os

# Chemin vers la base de données
DB_PATH = os.environ["TS_DB_PATH"]
CSV_PATH = os.environ["/Users/pnan9/my_files"]
CSV_TICKERS = os.path.join(CSV_PATH, "Tickers_list.csv")

def init_database():
    """Initialise la base de données et la table tickers_meta"""
    
    # Charger les tickers
    print("📂 Chargement des tickers...")
    df_tickers = pd.read_csv(CSV_TICKERS)
    symbols = df_tickers['Ticker'].tolist()
    print(f"   {len(symbols)} tickers chargés")
    
    # Créer la base de données (écrase si existe)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"🗑️  Base existante supprimée : {DB_PATH}")
    
    # Créer la connexion DuckDB
    conn = duckdb.connect(DB_PATH)
    
    # Créer la table tickers_meta avec le schéma demandé
    create_table_sql = """
    CREATE TABLE tickers_meta (
        symbol VARCHAR PRIMARY KEY,
        date_debut_dispo DATE,
        date_fin_dispo DATE,
        nb_enregistrements BIGINT,
        statut VARCHAR,
        dernier_essai TIMESTAMP,
        message_erreur TEXT
    );
    """
    
    conn.execute(create_table_sql)
    print("✅ Table tickers_meta créée")
    
    # Définir le watermark (date actuelle - 5 ans pour avoir 5 ans de données)
    today = datetime.now()
    watermark_date = today.date()
    five_years_ago = (today - timedelta(days=365*5)).date()
    
    print(f"📅 Watermark défini : {watermark_date}")
    print(f"📅 Date début historique : {five_years_ago}")
    
    # Initialiser tous les tickers en PENDING avec pandas
    init_df = pd.DataFrame([
        {
            'symbol': symbol,
            'date_debut_dispo': five_years_ago,
            'date_fin_dispo': watermark_date,
            'nb_enregistrements': 0,
            'statut': 'PENDING',
            'dernier_essai': None,
            'message_erreur': None
        }
        for symbol in symbols
    ])
    
    init_df.to_sql('tickers_meta', conn, if_exists='append', index=False)
    print(f"✅ {len(symbols)} tickers initialisés en PENDING")
    
    # Sauvegarder et fermer
    conn.commit()
    conn.close()
    
    print("\n🎉 Base de données initialisée avec succès !")
    return len(symbols)

if __name__ == "__main__":
    init_database()
