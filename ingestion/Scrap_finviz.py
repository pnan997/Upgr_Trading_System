import requests
import pandas as pd
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time 
import random as rnd

# --- DÉFINITIONS DU CACHE ET DES URLS ---

# DATA ENVIRONNEMENT ET VARIABLES GLOBALES


"""
views = [
    111,        #Overview
    121,        #Valuation
    161,        #Financial
    131,        #Ownership
    141,        #Performance
    171,        #Technical
    181,        #ETF
    191,        #ETF Perf
    151,        #Custom
    #341         #Snapshot
] 
"""

views = [111]
# Type de filtre (Actions/ETFs/Ensemble)
form_tb = '1'

# Utilisateur courant
 #userid = os.getlogin()
userid = 'pnan9'
# Chemins
#dir_path = f"/Users/{userid}/archive_python/Yfinance_big_picture/Data/.finviz/" # Dir du cache data
dir_path = '.finviz_cache' # Dir du cache data (dans le répertoire courant)
base_url = "https://finviz.com/screener.ashx?v="
#pathnam = f'/Users/{userid}/archive_python/Yfinance_big_picture/Data/'   # Là où on sauvegarde le résultat
pathnam = 'Data'   # Là où on sauvegarde le résultat (dans le répertoire courant)

# Critères de recherche
crits = ',f=geo_canada'

"""
NOUVEAUX CRITERES 
Catégorie de Filtre	        Filtre Finviz	                        Critère à Appliquer
-------------------         -------------                           -------------------
Valorisation & Qualité	    P/E (Price/Earnings)	                Under 20 (Inférieur à 20)
Valorisation Croissance	    PEG (Price/Earnings to Growth)	        Under 1 (Inférieur à 1)
Santé Financière	        Debt/Equity (Dette/Capitaux Propres)	Under 0.5 (Inférieur à 0.5)
Rentabilité	                Return on Equity (ROE)	                Over 15% (Supérieur à 15%)
Croissance Future	        EPS Growth Next 5Y	                    Over 15% (Supérieur à 15%)
Croissance Historique	    EPS Growth Past 5Y	                    Positive (Positive)
Momentum	                Performance (Quarter)	                Over 10% (Supérieur à 10%)
Intérêt du Marché	        Relative Volume	                        Over 1 (Supérieur à 1)

"""

# --- FONCTIONS DE BASE ---

def read_html(criteres, scr_type, f, r_start):
    """Lecture du HTML depuis le cache ou Finviz. r_start est l'index de ligne (1, 21, 41...)."""
    html=''
    # Utilise directement r_start fourni par la boucle principale (ex: r=1, r=21, ...)
    url=f'{base_url}{scr_type}&f={criteres}&ft={f}&r={r_start}'
    headers = {"User-Agent": "Mozilla/5.0"}
    fn = f"runOnce_{scr_type}_{r_start}.txt"
    filename = os.path.join(dir_path, fn)
    
    # Assurez-vous que le répertoire de cache existe
    os.makedirs(dir_path, exist_ok=True) 
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            html = file.read()
        print(f"Fichier cache '{fn}' utilisé.")
    except FileNotFoundError:
        print(f"Requête à Finviz pour l'URL: {url}")
        try:
            response = requests.get(url, headers=headers)
            time.sleep(5 + rnd.random() * 5) # Délai pour ne pas surcharger le site
            response.raise_for_status()
            html = response.text
            if cache_used is True:
                with open(filename, "w", encoding='utf-8') as file:
                    file.write(html)
                print(f"Finviz utilisé. Le fichier '{fn}' a été écrit'.")
        except requests.exceptions.RequestException as e:
            print(f"Erreur de requête: {e}")
            return ''

    return html

def get_finviz_sreener_pages(criteres, scr_type, f):
    """
    Récupère le nombre total d'enregistrements (total_stocks). 
    Cette valeur est utilisée pour déterminer le nombre de lignes à scraper.
    """
    html = read_html(criteres, scr_type, f, 1) # Toujours utiliser r=1 pour le total
    if not html: return 0

    soup = BeautifulSoup(html, "html.parser")
    
    element = soup.find("div", id="screener-total")
    if element and element.get_text():
        # Exemple de texte: "Rows 1-20 of 25". On extrait '25'.
        #print(f"Element : {element.get_text().split('/')[1].split('Total')[0]}")
        try:
            total_stocks = int(element.get_text().split('/')[1].split('Total')[0])
            return total_stocks
        except Exception as e:
            print(f"Erreur d'extraction du nombre total d'actions: {e}")
            return 0
    return 0

def get_finviz_screener_results(criteres, scr_type, f, r_start):
    """Récupère les données d'une seule page Finviz (commençant à r_start)."""
    html = read_html(criteres, scr_type, f, r_start)
    if not html: return None
    
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="styled-table-new")
    
    if table is None:
        return None
    
    # Extraire les noms de colonnes depuis le <thead>
    theader = table.find("thead")

    if theader is None :
        return None

    header_tags = table.find("thead").find_all("th")
    col_names = [th.get_text(strip=True) for th in header_tags]
    data = []
    rows = table.find_all("tr")[1:] # Saute le thead
    
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == len(col_names):
            data.append([col.get_text(strip=True) for col in cols])
    
    df = pd.DataFrame(data, columns=col_names)  
    return df

def chunks(lst, n):
    """Génère des paquets de taille n à partir d'une liste lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# NOTE : La fonction clean_and_convert_data a été retirée pour conserver les données brutes (string).

# --- DÉBUT DU PROGRAMME PRINCIPAL ---

print("📊 Lancement de l'agrégation Finviz...")

# Nous allons initialiser le DataFrame final
df_finviz = pd.DataFrame() 

########## DEFINIT L'Utilisation ou pas du cache
cache_used = False

# 1. Récupérer le nombre total d'enregistrements (stocks)
view_for_count = views[0]
total_records = get_finviz_sreener_pages(crits, view_for_count, form_tb)

if total_records == 0:
    print("❌ Pas d'actions trouvées selon les critères spécifiés.")
else:
    # Conversion en nombre de pages pour l'affichage uniquement
    num_pages = (total_records + 19) // 20
    print(f'👍 {total_records} actions trouvées. ({num_pages} pages). Démarrage de la collecte...')

    # Créer la liste des index de records (0 à total_records-1)
    pages = list(range(total_records))
    # L'itération utilisera chunks pour obtenir des index de départ (0, 20, 40, ...)

    # --- Boucle Extérieure: Itération sur les Views ---
    for view in views:
        print(f"\n--- Collecte de la Vue {view} ---")
        
        # results va contenir toutes les pages (tous les tickers) de la vue en cours.
        results = pd.DataFrame() 
        
        # --- Boucle Interne: Itération sur les Pages (par index de départ) ---
        for page_chunk in chunks(pages, 20):    
            # Calcul de l'index de départ Finviz 'r=' (1, 21, 41, ...)
            r_start = page_chunk[0] + 1
            
            print(f"   Récupération des lignes {r_start}-{r_start + len(page_chunk) - 1}...")
            
            df_page = get_finviz_screener_results(crits, view, form_tb, r_start)
            
            if df_page is not None and not df_page.empty:
                # Supprimer la colonne 'No.' (index de ligne Finviz)
                if 'No.' in df_page.columns:
                    df_page = df_page.drop(columns=['No.'])
                
                # **1. Agrégation des pages dans results**
                results = pd.concat([results, df_page], ignore_index=True)
            elif df_page is None or df_page.empty:
                # Si l'API ne retourne plus rien, on arrête la boucle interne pour cette vue.
                print(f"   Fin des résultats ou erreur de scraping pour r={r_start}. Arrêt du bouclage des pages pour cette vue.")
                break
        
        # --- Fin de la Boucle Interne des Pages ---

        if not results.empty:
            # **2. Préparation pour l'Agrégation des Vues (Fusion)**
            
            # Assurez-vous que le Ticker est unique dans cette vue avant de le définir comme index.
            results = results.drop_duplicates(subset=['Ticker'])
            
            # Définir 'Ticker' comme index pour permettre la fusion basée sur le Ticker.
            results_indexed = results.set_index('Ticker')

            if df_finviz.empty:
                # Première vue, on l'utilise pour initialiser le DataFrame final
                df_finviz = results_indexed
                print(f"   Vue {view} initialisée. Total Tickers: {len(df_finviz)}")
            else:
                # Joindre les données de la nouvelle vue au DataFrame final
                df_finviz = df_finviz.join(
                    results_indexed, 
                    how='outer', 
                    lsuffix='', 
                    rsuffix=f'_v{view}'
                )
                print(f"   Vue {view} agrégée. Tickers uniques: {len(df_finviz)}")
        else:
            print(f"   Vue {view} n'a retourné aucune donnée après agrégation des pages.")

# --- Fin de la Boucle Extérieure des Views ---

# Nettoyage final des colonnes en double 

if not df_finviz.empty:
    print("\n--- Nettoyage final du DataFrame ---")
    
    # Réinitialiser l'index 'Ticker' pour qu'il soit une colonne normale
    df_finviz = df_finviz.reset_index()
    
    # Trouver les colonnes dupliquées et fusionner les valeurs non-NaN
    base_columns = [col for col in df_finviz.columns if not any(col.endswith(f'_v{v}') for v in views)]

    for base_col in base_columns:
        # Trouver toutes les colonnes qui correspondent à ce nom (ex: 'Prix', 'Prix_v121', 'Prix_v161')
        duplicate_cols = [col for col in df_finviz.columns if col == base_col or col.startswith(f'{base_col}_v')]
        
        if len(duplicate_cols) > 1:
            print(f"   Fusion des colonnes dupliquées pour '{base_col}'...")
            
            # Utiliser la première valeur non-NaN disponible pour chaque ligne. 
            # Les données brutes (string) sont conservées.
            df_finviz[base_col] = df_finviz[duplicate_cols].bfill(axis=1).iloc[:, 0]
            
            # Supprimer toutes les colonnes dupliquées suffixées
            cols_to_drop = [col for col in duplicate_cols if col != base_col]
            df_finviz = df_finviz.drop(columns=cols_to_drop)

    # Afficher les premières lignes du résultat final
    print("\n✅ DataFrame Finviz Final (DF_FINVIZ) :")
    print(df_finviz.head().to_markdown(index=False))

    # Sauvegarde du résultat
    today = datetime.now().strftime("%Y%m%d")
    output_file = os.path.join(pathnam, f'Finviz_Screener_Results_{today}.xlsx')
    
    # Assurez-vous que le répertoire de sauvegarde existe
    os.makedirs(pathnam, exist_ok=True) 

    df_finviz.to_excel(output_file, index=False)
    print(f"\nSauvegarde réussie : {output_file}")
    print(f"Total des colonnes uniques: {len(df_finviz.columns)}")

else:
    print("Le DataFrame final est vide. Aucune donnée n'a été collectée.")
