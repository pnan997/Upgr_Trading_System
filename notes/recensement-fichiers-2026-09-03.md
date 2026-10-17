# Recensement des fichiers — Trading_System
*Généré le 03/09/2026 · racine `/Users/pnan9/Trading_System/`*

**Objectif** : aide à la décision de suppression. Ne sont listés que les fichiers *données / sorties / sauvegardes / logs / notes / images / modèles*.

## Analyse du problème de cash

### Contexte
Le fichier `Paper_Trading/logs/launchd_ibkr.log` contient un avertissement important :
```
WARNING: derive de cash inattendue (+8485.85 $, seuil 5005.93 $) -- attendu 991207.27 $, observe 999693.12 $. Voir events log.
```

### Analyse détaillée
Le fichier `Paper_Trading/logs/ibkr_events_20260903_153018.json` montre :
- Fonds disponibles attendus : 991207.27 $
- Fonds disponibles observés : 999693.12 $
- Différence : +8485.85 $

### Hypothèses
1. Le script calcule l'exposition des positions existantes via `current_exposure()` qui utilise `avgCost`
2. Les positions ouvertes sont de 4909$ et 4878$ (total ~9787$)
3. Cette valeur est proche de la différence de 8485.85$ détectée
4. Cela suggère que le script ne tient peut-être pas compte correctement des positions existantes dans le calcul

### Problème potentiel
Le script peut avoir une incohérence dans le calcul du cash disponible :
- Il calcule `exposure_before` (valeur d'acquisition des positions existantes)
- Mais peut ne pas correctement ajuster le cash disponible en tenant compte de cette exposition
- Ou il utilise la valeur d'acquisition au lieu de la valeur de marché

### Prochaines étapes
1. Vérifier le fonctionnement de `current_exposure()` et comment il calcule les positions
2. Comparer les montants des positions ouvertes avec les différences de cash observées
3. Vérifier si le script tient compte correctement de la valeur de marché des positions existantes
4. Étudier les différences entre `avgCost` et la valeur actuelle des positions

**Règle d'exclusion (demandée)** : **programmes** (`.py .ipynb .sh .c .so .pyc …` + `__pycache__`) et **fichiers de configuration** (`.json .yaml .toml .env .plist.template …`) sont *exclus* de la liste principale — ils restent fonctionnels. Leurs tailles agrégées figurent en §3 pour la transparence.
**Critère d'âge** : **⛔>3j** = non modifié depuis le **31/08/2026** (3 jours avant aujourd'hui). Un ancien fichier sur lequel on ne peut plus rien faire = candidat à la suppression.

> Tri **du plus lourd au plus léger** dans chaque dossier. Colonne « Âge » = jours depuis la dernière modification.

## 1. Synthèse par répertoire

| Répertoire | Fichiers | Taille | dont >3j | Taille >3j | Plus ancien |
|---|--:|--:|--:|--:|:--:|
| `Paper_Trading` | 115 | 9.3 Go | 85 | 6.8 Go | 28/07/2026 |
| `Sauves` | 1 | 1.0 Go | 0 | 0 o | 02/09/2026 |
| `Features_Pente` | 28 | 656.0 Mo | 28 | 656.0 Mo | 24/07/2026 |
| `Features_Pente_Walk_Forward` | 4 | 261.4 Mo | 4 | 261.4 Mo | 24/07/2026 |
| `atelier` | 19 | 1.7 Mo | 19 | 1.7 Mo | 24/07/2026 |
| `Data` | 9 | 323.4 Ko | 9 | 323.4 Ko | 24/07/2026 |
| `SP500` | 4 | 230.6 Ko | 4 | 230.6 Ko | 25/07/2026 |
| `logs` | 5 | 179.7 Ko | 0 | 0 o | 02/09/2026 |
| `ingestion` | 2 | 21.0 Ko | 2 | 21.0 Ko | 24/07/2026 |
| `distribution` | 2 | 16.8 Ko | 2 | 16.8 Ko | 24/07/2026 |
| `notes` | 3 | 10.8 Ko | 2 | 786 o | 24/07/2026 |
| `Documentation` | 2 | 8.9 Ko | 2 | 8.9 Ko | 26/07/2026 |
| `.` | 4 | 989 o | 3 | 683 o | 24/07/2026 |
| **TOTAL** | **198** | **11.2 Go** | **160** | **7.7 Go** | |

*11.2 Go à évaluer, dont **7.7 Go** datant de >3 j. Deux tiers du disque = `Paper_Trading` (9,3 Go) + `Sauves` (1 Go).*

## 2. Détail par répertoire

### `Paper_Trading` — 9.3 Go (115 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| **650.1 Mo** | 18/08/2026 | 15 j | `Data/run_20260818_110002/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **649.9 Mo** | 19/08/2026 | 14 j | `Data/run_20260819_091842/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **649.9 Mo** | 19/08/2026 | 14 j | `Data/run_20260819_110004/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **648.7 Mo** | 20/08/2026 | 13 j | `Data/run_20260820_110004/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **647.5 Mo** | 24/08/2026 | 9 j | `Data/run_20260824_110004/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **647.5 Mo** | 21/08/2026 | 12 j | `Data/run_20260821_110005/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **646.6 Mo** | 25/08/2026 | 8 j | `Data/run_20260825_110006/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **645.7 Mo** | 26/08/2026 | 7 j | `Data/run_20260826_110005/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **645.5 Mo** | 28/08/2026 | 5 j | `Data/run_20260828_110005/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **645.5 Mo** | 27/08/2026 | 6 j | `Data/run_20260827_110004/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders)  ⛔>3j |
| **644.3 Mo** | 31/08/2026 | 2 j | `Data/run_20260831_110005/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders) |
| **643.1 Mo** | 01/09/2026 | 1 j | `Data/run_20260901_110002/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders) |
| **642.2 Mo** | 02/09/2026 | 0 j | `Data/run_20260902_110004/` — run quotidien (6 fichiers : features, ohlcv, candidates, orders) |
| 364.0 Mo | 18/08/2026 | 15 j | `Paper_Trading/model/knn_model.joblib`  ⛔>3j |
| 314.4 Mo | 02/09/2026 | 0 j | `Paper_Trading/Data/train_features.csv` |
| 148.2 Mo | 02/09/2026 | 0 j | `Paper_Trading/Data/test_features_with_predictions_ohlcv.csv` |
| 91.3 Mo | 02/09/2026 | 0 j | `Paper_Trading/Data/test_features.csv` |
| 88.2 Mo | 02/09/2026 | 0 j | `Paper_Trading/Data/test_features_with_predictions.csv` |
| 61.7 Mo | 18/08/2026 | 15 j | `Paper_Trading/Data/archive/test_features_with_predictions_ohlcv.csv.gz`  ⛔>3j |
| 39.2 Mo | 18/08/2026 | 15 j | `Paper_Trading/Data/archive/test_features_with_predictions.csv.gz`  ⛔>3j |
| 27.2 Ko | 02/09/2026 | 0 j | `Paper_Trading/logs/launchd_ibkr.log` |
| 5.2 Ko | 02/09/2026 | 0 j | `Paper_Trading/logs/launchd_pipeline.log` |
| 3.5 Ko | 18/08/2026 | 15 j | `Paper_Trading/logs/pipeline_20260818_110002.log`  ⛔>3j |
| 3.0 Ko | 28/07/2026 | 36 j | `Paper_Trading/atelier/README.md`  ⛔>3j |
| 2.3 Ko | 26/08/2026 | 7 j | `Paper_Trading/logs/pipeline_20260826_110005.log`  ⛔>3j |
| 2.3 Ko | 19/08/2026 | 14 j | `Paper_Trading/logs/pipeline_20260819_110004.log`  ⛔>3j |
| 2.3 Ko | 02/09/2026 | 0 j | `Paper_Trading/logs/pipeline_20260902_110004.log` |
| 2.3 Ko | 27/08/2026 | 6 j | `Paper_Trading/logs/pipeline_20260827_110004.log`  ⛔>3j |
| 2.3 Ko | 01/09/2026 | 1 j | `Paper_Trading/logs/pipeline_20260901_110002.log` |
| 2.3 Ko | 31/08/2026 | 2 j | `Paper_Trading/logs/pipeline_20260831_110005.log` |
| 2.3 Ko | 19/08/2026 | 14 j | `Paper_Trading/logs/pipeline_20260819_091842.log`  ⛔>3j |
| 2.3 Ko | 28/08/2026 | 5 j | `Paper_Trading/logs/pipeline_20260828_110005.log`  ⛔>3j |
| 2.3 Ko | 24/08/2026 | 9 j | `Paper_Trading/logs/pipeline_20260824_110004.log`  ⛔>3j |
| 2.3 Ko | 21/08/2026 | 12 j | `Paper_Trading/logs/pipeline_20260821_110005.log`  ⛔>3j |
| 2.3 Ko | 20/08/2026 | 13 j | `Paper_Trading/logs/pipeline_20260820_110004.log`  ⛔>3j |
| 2.3 Ko | 25/08/2026 | 8 j | `Paper_Trading/logs/pipeline_20260825_110006.log`  ⛔>3j |
| 959 o | 18/08/2026 | 15 j | `Paper_Trading/model/scaler.joblib`  ⛔>3j |
| 956 o | 02/09/2026 | 0 j | `Paper_Trading/Data/latest_prepared_orders.csv` |
| 618 o | 24/08/2026 | 9 j | `Paper_Trading/Data/ibkr_orders_20260824_153130.csv`  ⛔>3j |
| 481 o | 02/09/2026 | 0 j | `Paper_Trading/Data/ibkr_orders_20260902_153006.csv` |
| 476 o | 28/08/2026 | 5 j | `Paper_Trading/Data/ibkr_orders_20260828_153013.csv`  ⛔>3j |
| 388 o | 18/08/2026 | 15 j | `Paper_Trading/Data/archive/manifest.json.gz`  ⛔>3j |
| 352 o | 19/08/2026 | 14 j | `Paper_Trading/Data/ibkr_orders_20260819_103003.csv`  ⛔>3j |
| 308 o | 18/08/2026 | 15 j | `Paper_Trading/logs/archive/pipeline_20260728_092340.log.gz`  ⛔>3j |
| 269 o | 01/09/2026 | 1 j | `Paper_Trading/Data/ibkr_orders_20260901_150010.csv` |
| 266 o | 20/08/2026 | 13 j | `Paper_Trading/Data/ibkr_orders_20260820_155606.csv`  ⛔>3j |
| 264 o | 21/08/2026 | 12 j | `Paper_Trading/Data/ibkr_orders_20260821_153106.csv`  ⛔>3j |
| 118 o | 18/08/2026 | 15 j | `Paper_Trading/Data/archive/candidates_20260728_092340.csv.gz`  ⛔>3j |
| 57 o | 18/08/2026 | 15 j | `Paper_Trading/Data/archive/prepared_orders_20260728_092340.csv.gz`  ⛔>3j |
| 48 o | 18/08/2026 | 15 j | `Paper_Trading/Data/archive/latest_prepared_orders.csv.gz`  ⛔>3j |

### `Sauves` — 1.0 Go (1 fichier)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 1.0 Go | 02/09/2026 | 0 j | `Sauves/tickers_meta_20260902.db.bak` |

### `Features_Pente` — 656.0 Mo (28 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 300.8 Mo | 24/07/2026 | 40 j | `Features_Pente/train_features.csv`  ⛔>3j |
| 156.2 Mo | 24/07/2026 | 40 j | `Features_Pente/test_features_with_predictions_ohlcv.csv`  ⛔>3j |
| 100.9 Mo | 24/07/2026 | 40 j | `Features_Pente/test_features.csv`  ⛔>3j |
| 97.5 Mo | 24/07/2026 | 40 j | `Features_Pente/test_features_with_predictions.csv`  ⛔>3j |
| 320.2 Ko | 24/07/2026 | 40 j | `Features_Pente/features_pente.csv`  ⛔>3j |
| 58.6 Ko | 24/07/2026 | 40 j | `Features_Pente/historique_résultats/knn_backtest.journal_15_06_2.csv`  ⛔>3j |
| 58.6 Ko | 24/07/2026 | 40 j | `Features_Pente/historique_résultats/knn_backtest.journal_15_06_1.csv`  ⛔>3j |
| 57.5 Ko | 24/07/2026 | 40 j | `Features_Pente/knn_backtest.journal.csv`  ⛔>3j |
| 20.6 Ko | 24/07/2026 | 40 j | `Features_Pente/knn_backtest.equity.csv`  ⛔>3j |
| 20.6 Ko | 24/07/2026 | 40 j | `Features_Pente/historique_résultats/knn_backtest.equity_15_06_1.csv`  ⛔>3j |
| 20.6 Ko | 24/07/2026 | 40 j | `Features_Pente/historique_résultats/knn_backtest.equity_15_06_2.csv`  ⛔>3j |
| 7.9 Ko | 24/07/2026 | 40 j | `Features_Pente/contexte4.md`  ⛔>3j |
| 6.2 Ko | 24/07/2026 | 40 j | `Features_Pente/enrich_predictions.stdout`  ⛔>3j |
| 6.2 Ko | 24/07/2026 | 40 j | `Features_Pente/enrich_predictions.log`  ⛔>3j |
| 5.3 Ko | 24/07/2026 | 40 j | `Features_Pente/knn_backtest.log`  ⛔>3j |
| 5.2 Ko | 24/07/2026 | 40 j | `Features_Pente/atelier/Corrections_knn_backtest`  ⛔>3j |
| 3.7 Ko | 24/07/2026 | 40 j | `Features_Pente/Probabilités.md`  ⛔>3j |
| 3.4 Ko | 24/07/2026 | 40 j | `Features_Pente/notes/A_envisager.md`  ⛔>3j |
| 3.1 Ko | 24/07/2026 | 40 j | `Features_Pente/last_conversation.md`  ⛔>3j |
| 2.1 Ko | 24/07/2026 | 40 j | `Features_Pente/contexte3.md`  ⛔>3j |
| 2.0 Ko | 24/07/2026 | 40 j | `Features_Pente/plan1.md`  ⛔>3j |
| 1.4 Ko | 24/07/2026 | 40 j | `Features_Pente/contexte2.md`  ⛔>3j |
| 1007 o | 24/07/2026 | 40 j | `Features_Pente/contexte1.md`  ⛔>3j |
| 751 o | 24/07/2026 | 40 j | `Features_Pente/knn_backtest.summary.csv`  ⛔>3j |
| 748 o | 24/07/2026 | 40 j | `Features_Pente/historique_résultats/knn_backtest.summary_15_06_2.csv`  ⛔>3j |
| 720 o | 24/07/2026 | 40 j | `Features_Pente/historique_résultats/knn_backtest.summary_15_06_1.csv`  ⛔>3j |
| 375 o | 24/07/2026 | 40 j | `Features_Pente/notes/Exposition_cash.md`  ⛔>3j |
| 80 o | 24/07/2026 | 40 j | `Features_Pente/paramètres_knn.backtest`  ⛔>3j |

### `Features_Pente_Walk_Forward` — 261.4 Mo (4 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 163.9 Mo | 24/07/2026 | 40 j | `Features_Pente_Walk_Forward/test_features_with_predictions_ohlcv.csv`  ⛔>3j |
| 97.5 Mo | 24/07/2026 | 40 j | `Features_Pente_Walk_Forward/test_features_with_predictions.csv`  ⛔>3j |
| 2.9 Ko | 24/07/2026 | 40 j | `Features_Pente_Walk_Forward/notes/A_envisager.md`  ⛔>3j |
| 375 o | 24/07/2026 | 40 j | `Features_Pente_Walk_Forward/notes/Exposition_cash.md`  ⛔>3j |

### `atelier` — 1.7 Mo (19 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 188.4 Ko | 24/07/2026 | 40 j | `atelier/LI_multi_fenetres.png`  ⛔>3j |
| 178.7 Ko | 24/07/2026 | 40 j | `atelier/XPEV_multi_fenetres.png`  ⛔>3j |
| 171.8 Ko | 24/07/2026 | 40 j | `atelier/AAPL_multi_fenetres.png`  ⛔>3j |
| 165.2 Ko | 24/07/2026 | 40 j | `atelier/Exercice1.ipynb.bak_20260601`  ⛔>3j |
| 154.6 Ko | 24/07/2026 | 40 j | `atelier/LI_distribution.png`  ⛔>3j |
| 151.3 Ko | 24/07/2026 | 40 j | `atelier/XPEV_distribution.png`  ⛔>3j |
| 143.4 Ko | 24/07/2026 | 40 j | `atelier/AAPL_distribution.png`  ⛔>3j |
| 108.5 Ko | 24/07/2026 | 40 j | `atelier/Exercice1.ipynb.bak_ai_step_20260602`  ⛔>3j |
| 108.2 Ko | 24/07/2026 | 40 j | `atelier/Exercice1.ipynb.bak_gspc_benchmark_20260601`  ⛔>3j |
| 105.0 Ko | 24/07/2026 | 40 j | `atelier/comparaison_XPEV_vs_LI.png`  ⛔>3j |
| 99.1 Ko | 24/07/2026 | 40 j | `atelier/comparaison_AAPL_vs_MSFT.png`  ⛔>3j |
| 92.1 Ko | 24/07/2026 | 40 j | `atelier/Exercice1.ipynb.bak_validation_20260601`  ⛔>3j |
| 59.3 Ko | 24/07/2026 | 40 j | `atelier/Exercice1.ipynb.bak_var_cvar_20260601`  ⛔>3j |
| 28.4 Ko | 24/07/2026 | 40 j | `atelier/cours_distribution.html`  ⛔>3j |
| 11.0 Ko | 24/07/2026 | 40 j | `atelier/Features_Eng.md`  ⛔>3j |
| 3.1 Ko | 24/07/2026 | 40 j | `atelier/paper_trading.journal.csv`  ⛔>3j |
| 1.9 Ko | 24/07/2026 | 40 j | `atelier/paper_trading.init`  ⛔>3j |
| 1.8 Ko | 24/07/2026 | 40 j | `atelier/prompt_features_pente.md`  ⛔>3j |
| 568 o | 24/07/2026 | 40 j | `atelier/paper_trading.summary.csv`  ⛔>3j |

### `Data` — 323.4 Ko (9 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 129.3 Ko | 24/07/2026 | 40 j | `Data/Finviz_Screener_Results_20260411_Nyse.xlsx`  ⛔>3j |
| 97.6 Ko | 24/07/2026 | 40 j | `Data/Finviz_Screener_Results_20260411_Nasdaq.xlsx`  ⛔>3j |
| 52.4 Ko | 24/07/2026 | 40 j | `Data/constituents.csv`  ⛔>3j |
| 21.0 Ko | 24/07/2026 | 40 j | `Data/anomalies.csv`  ⛔>3j |
| 11.3 Ko | 27/07/2026 | 37 j | `Data/process_error_tickers_report.txt`  ⛔>3j |
| 10.6 Ko | 24/07/2026 | 40 j | `Data/differences_secteurs.csv`  ⛔>3j |
| 572 o | 26/07/2026 | 38 j | `Data/tickers_a_verifier.csv`  ⛔>3j |
| 467 o | 24/07/2026 | 40 j | `Data/comparaison_secteurs.csv`  ⛔>3j |
| 206 o | 24/07/2026 | 40 j | `Data/sector-counts.csv`  ⛔>3j |

### `SP500` — 230.6 Ko (4 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 225.7 Ko | 25/07/2026 | 39 j | `SP500/Data/sector_contents.csv`  ⛔>3j |
| 3.2 Ko | 25/07/2026 | 39 j | `SP500/news_Total.csv`  ⛔>3j |
| 1.8 Ko | 25/07/2026 | 39 j | `SP500/Data/news_CCJ.csv`  ⛔>3j |
| 0 o | 25/07/2026 | 39 j | `SP500/Data/MSCI_CHINA.csv`  ⛔>3j |

### `logs` — 179.7 Ko (5 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 84.7 Ko | 02/09/2026 | 0 j | `logs/delta_batch.log` |
| 79.5 Ko | 02/09/2026 | 0 j | `logs/delta_retry.log` |
| 8.0 Ko | 03/09/2026 | 0 j | `logs/sector_update.log` |
| 5.7 Ko | 02/09/2026 | 0 j | `logs/tickers_errors.log` |
| 1.8 Ko | 02/09/2026 | 0 j | `logs/svgd.log` |

### `ingestion` — 21.0 Ko (2 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 12.0 Ko | 24/07/2026 | 40 j | `ingestion/tickers_meta.db`  ⛔>3j |
| 9.0 Ko | 24/07/2026 | 40 j | `ingestion/gspc_complement.csv`  ⛔>3j |

### `distribution` — 16.8 Ko (2 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 10.1 Ko | 24/07/2026 | 40 j | `distribution/resultats_screening_20260518.csv`  ⛔>3j |
| 6.7 Ko | 24/07/2026 | 40 j | `distribution/screening long quality.md`  ⛔>3j |

### `notes` — 10.8 Ko (3 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 10.0 Ko | 02/09/2026 | 0 j | `notes/revue-coherence-pipeline-paper-trading-2026-09-02.md` |
| 475 o | 24/07/2026 | 40 j | `notes/Infos_distribution.md`  ⛔>3j |
| 311 o | 24/07/2026 | 40 j | `notes/Projet Kalmann`  ⛔>3j |

### `Documentation` — 8.9 Ko (2 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 7.0 Ko | 26/07/2026 | 38 j | `Documentation/launchd_reference.md`  ⛔>3j |
| 1.9 Ko | 18/08/2026 | 15 j | `Documentation/charte-documentation-trading-system.md`  ⛔>3j |

### `.` — 989 o (4 fichiers)

| Taille | Modifié | Âge | Chemin |
|--:|:--:|:--:|---|
| 683 o | 27/07/2026 | 37 j | `ancien_crontab.txt`  ⛔>3j |
| 306 o | 02/09/2026 | 0 j | `tickers_errors.csv` |
| 0 o | 24/07/2026 | 40 j | `CONTEXTE.md`  ⛔>3j |
| 0 o | 24/07/2026 | 40 j | `README.md`  ⛔>3j |

## 3. Exclu de la liste principale (fonctionnel — à ne pas supprimer)

| Élément | Type | Taille | Remarque |
|---|---|--:|---|
| `.git` | infrastructure (historique) | 521.7 Mo | un `git gc` peut réduire |
| `.venv` | programmes (dépendances) | 264.3 Mo | environnement Python, recréable (`uv sync`) |
| `.direnv` | configuration | 5.3 Mo | fichiers d'environnement |
| `.github` | configuration (CI) | 4.3 Ko | actions |
| **Programmes** `.py .ipynb .sh .c .so …` | code | 3.3 Mo | 93 fichiers |
| **Configuration** `.json .yaml .toml .env …` | config | 251.0 Ko | 42 fichiers |

*Total disque du projet : **12.0 Go** — dont 11.2 Go à évaluer, 791.3 Mo infrastructure, 3.3 Mo programmes, 251.0 Ko config.*

## 4. Repères pour la décision

- **`Paper_Trading/Data/run_*`** : 13 runs quotidiens ≈ 650 Mo chacun (≈ 8,4 Go au total), dont 10 datant de >3j (≈ 6,3 Go). C'est le poste le plus lourd. À trancher : *garder les N derniers jours / ne garder que `Data/archive/` (déjà compressée en .gz, ~100 Mo) / supprimer les runs antérieurs à la date choisie*.
- **`Paper_Trading/model/*.joblib`** (364 Mo) : modèle + scaler entraînés — **fonctionnels**, à conserver (à ne pas confondre avec les runs).
- **`Paper_Trading/Data/{train,test}_features*.csv`** (≈ 640 Mo, 02/09) : copies « latest » des sorties actuelles — récentes, à laisser.
- **`Sauves/tickers_meta_20260902.db.bak`** : 1 Go, daté du 02/09. Sauvegarde de base — à ne supprimer qu'une fois remplacée par une sauvegarde plus récente.
- **`Features_Pente` (656 Mo) / `Features_Pente_Walk_Forward` (261 Mo)** : gros CSV de features du 24/07, tous ⛔>3j. Bons candidats si plus utilisés pour l'entraînement.
- **`atelier/*.ipynb.bak_*`** : 5 sauvegardes de notebook (juillet) — petites mais redondantes.
- **`logs/` & `Paper_Trading/logs/`** : récents (02–03/09), légers — à laisser.
- **`Data/`, `SP500/`, `ingestion/`, `distribution/`, `Documentation/`** : tous ⛔>3j et légers (<330 Ko) — bas risque, à vérifier rapidement. (`Utils/` ne contient que du code → exclu.)
- **`ingestion/tickers_meta.db`** (12 Ko) : base de travail — fonctionnelle ; elle est par ailleurs sauvegardée dans `Sauves/` (1 Go). Ne pas supprimer tant qu'elle est en service.
