# État du système au 17/10/2026 — backtest KNN avec frais

À relire avant de se reposer des questions déjà traitées. Projet : `Upgr_Trading_System/Features_Pente_Walk_Forward/atelier/`.

## 1. Ce qu'on a

Un walk-forward complet refait le 17/10, avec frais et slippage, par `walk_forward.py` (config : `walk_forward_config.json`). Pour chaque section, 4 programmes enchaînés :

1. `generate_training_dataset.py` — features, séparation train / test
2. `generate_predictions_and_save.py` — entraînement sur le train, prédictions sur le test
3. `enrich_predictions.py` — ajout des prix
4. `knn_backtest.py` — backtest de la section (config : `knn_backtest_config.json`)

Découpage (jours de bourse) : train 252, gap 10, test 61, pas 61. Premier train à la 1re date de features (2021-03-30, soit base + ~60 j pour le slope 60). 19 sections (la dernière tronquée à 35 j de test), 16 min de calcul. Sorties : `wf_sections/sectionXX_<debut>_<fin>/`, `walk_forward_resume.csv` et `.md`.

## 2. Paramètres du backtest

- Signal prediction = 1 du jour D-1 → entrée à l'Open de D ; TP 1,5 % / SL 0,6 % ; seed 42
- Capital 30 000, budget engagé 15 000 (3 lots, entre 2 500 et 5 000) ; candidats tirés au hasard dans le pool
- Filtre prix : Close(D-1) ≥ 9 $
- Frais : modèle IBKR Tiered (valeurs de départ dans le JSON, **frais réglementaires à vérifier**)
- Slippage (**hypothèses, non mesurées**) : entrée 0,05 %, sortie TP 0 %, sortie SL 0,10 %, gap 0,10 %
- Chaque section = backtest indépendant (on repart de zéro ; positions ouvertes en fin de section annulées à PnL 0)

## 3. Résultats (walk-forward du 17/10)

2 785 trades — PnL brut 37 587 — frais 4 218 — slippage 15 388 — **PnL net 17 981**.
3 sections négatives sur 19 (09 : mars-juin 2024 ; 11 ; 19 partielle). Les 3 dernières sections complètes sont les meilleures (+7 à +9 %). Win rate de 30 % à 52 % selon la période ; seuil de rentabilité net ≈ 36 % de trades gagnants.

## 4. Hypothèses et limites (non vérifiées)

- **Slippage non mesuré** : le net tombe vers zéro si le slippage réel vaut environ 2,2 fois les hypothèses. À mesurer sur 20-30 ordres réels, même petits.
- **Durée max d'une étiquette (TP/SL) vs gap de 10 jours** : jamais comparée. Si l'étiquette dépasse 10 jours de bourse, les prédictions sont un peu optimistes.
- **Volume non contrôlé** dans le backtest (pas de filtre de liquidité à part le prix ≥ 9 $).
- **Max drawdown** donné par section (3 mois), pas sur la période entière.
- **Une seule seed (42)** : le tirage au hasard fait varier le net de plusieurs milliers d'euros d'une seed à l'autre.
- **Ne pas réutiliser** `etude_sensibilite.md` du 16/10 (grille de slippage, seeds, TP/SL alternatifs) : elle porte sur l'ancien fichier de prédictions, d'origine non reproductible. TP/SL fixes 1,5 / 0,6 sont conservés par défaut.

## 5. Décisions prises

- Walk-forward : 1 an de train, 61 jours de test, pas de 61 jours (cohérent avec le réentraînement du paper trading)
- Filtre prix plancher 9 $ (raison : commissions disproportionnées sur petites valeurs, fragmentation des lots) ; gain de PnL non démontré
- Un seul chantier à la fois ; `Upgr_Trading_System` d'abord, `Trading_System` plus tard

## 6. Question ouverte

**Le KNN apporte-t-il quelque chose par rapport au hasard ?** Pas tranché sur ces données. Test prévu : même backtest, même walk-forward, en remplaçant le pool « prediction = 1 » par l'ensemble des candidats, toutes choses égales par ailleurs.
