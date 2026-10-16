#!/usr/bin/env python3
"""
### ** ATTENTION ** : BOMBE ATOMIQUE ! Ce script remplace TOUTES les données sur 5 ans!

Script pour télécharger et enregistrer les données OHLCV d'un ticker dans DuckDB
"""

import duckdb
import yfinance as yf
from datetime import datetime, timedelta
import os

# Chemin vers la base de données
DB_PATH = os.environ["TS_DB_PATH"]

def download_ticker(symbol):
    """Télécharge et enregistre les données OHLCV d'un ticker"""
    
    print(f"\n📥 Téléchargement de {symbol}...")
    
    conn = duckdb.connect(DB_PATH)
    
    # Récupérer le statut actuel du ticker
    current_status = conn.execute(
        "SELECT statut, date_debut_dispo, date_fin_dispo FROM tickers_meta WHERE symbol = ?",
        [symbol]
    ).fetchone()
    
    if not current_status:
        print(f"   ⚠️  Ticker {symbol} non trouvé dans la meta")
        conn.close()
        return False
    
    statut, date_debut_dispo, date_fin_dispo = current_status
    
    # Si PENDING, télécharger les données
    if statut == 'PENDING':
        print(f"   ⏳ Statut: {statut}, Date début: {date_debut_dispo}, Date fin: {date_fin_dispo}")
        
        # Calculer la période de téléchargement (5 ans)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*5)
        
        print(f"   📅 Période: {start_date.date()} à {end_date.date()}")
        
        # Télécharger les données avec yfinance
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
            
            if df.empty:
                print(f"   ❌ Aucune donnée disponible pour {symbol}")
                # Mettre à jour le statut avec erreur
                conn.execute("""
                    UPDATE tickers_meta 
                    SET statut = 'ERROR', message_erreur = ?
                    WHERE symbol = ?
                """, [f"Aucune donnée disponible pour {symbol}", symbol])
                conn.commit()
                conn.close()
                return False
            
            print(f"   ✅ Données téléchargées: {len(df)} barres")
            
            # Créer la table OHLCV pour ce ticker si elle n'existe pas
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS ohlcv_{symbol.replace('.', '_').replace('-', '')} (
                date DATE PRIMARY KEY,
                open FLOAT,
                high FLOAT,
                low FLOAT,
                close FLOAT,
                volume BIGINT
            );
            """
            conn.execute(create_table_sql)
            
            # Insérer les données
            insert_sql = f"""
            INSERT INTO ohlcv_{symbol.replace('.', '_').replace('-', '')} (date, open, high, low, close, volume)
            SELECT 
                date(date) as date,
                open,
                high,
                low,
                close,
                volume
            FROM df;
            """
            conn.execute(insert_sql)
            
            # Mettre à jour le statut
            conn.execute(f"""
                UPDATE tickers_meta 
                SET statut = 'COMPLETED', nb_enregistrements = ?, dernier_essai = ?
                WHERE symbol = ?
            """, [len(df), datetime.now(), symbol])
            conn.commit()
            
            print(f"   ✅ Ticker {symbol} marqué comme COMPLETED")
            
        except Exception as e:
            print(f"   ❌ Erreur lors du téléchargement de {symbol}: {str(e)}")
            # Mettre à jour le statut avec erreur
            conn.execute(f"""
                UPDATE tickers_meta 
                SET statut = 'ERROR', message_erreur = ?, dernier_essai = ?
                WHERE symbol = ?
            """, [f"Erreur: {str(e)}", datetime.now(), symbol])
            conn.commit()
            
    elif statut == 'COMPLETED':
        print(f"   ✅ Ticker {symbol} déjà COMPLETED ({current_status[2]} barres)")
    
    elif statut == 'ERROR':
        print(f"   ⚠️  Ticker {symbol} en erreur: {statut}")
    
    conn.close()
    return True

def download_multiple_tickers(symbols):
    """Télécharge les données pour plusieurs tickers"""
    
    print(f"\n📥 Téléchargement de {len(symbols)} tickers...")
    
    success_count = 0
    error_count = 0
    
    for symbol in symbols:
        try:
            if download_ticker(symbol):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"   ❌ Erreur pour {symbol}: {str(e)}")
            error_count += 1
    
    print(f"\n📊 Résumé:")
    print(f"   ✅ Succès: {success_count}")
    print(f"   ❌ Échecs: {error_count}")
    
    return success_count, error_count

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Télécharger un ticker spécifique
        symbol = sys.argv[1]
        download_ticker(symbol)
    else:
        # Afficher l'aide
        print("Usage:")
        print("  python download_ticker.py <SYMBOL>   - Télécharger un ticker spécifique")
        print("  python download_ticker.py            - Afficher l'aide")
