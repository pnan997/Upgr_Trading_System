# Backtest KNN : filtre prix, frais de transaction et slippage

---

## But et moyens (langage python)

Modifier le programme existant `Upgr_Trading_System/Features_Pente_Walk_Forward/atelier/knn_backtest.py` (et son `knn_backtest_config.json`) pour que le backtest devienne **réaliste** : il ne modélise aujourd'hui ni frais ni slippage, donc ses résultats sont trop optimistes.

Trois modifications, et **seulement** celles-ci :
1. Filtre des tickers à moins de 9 $
2. Frais de transaction aller et retour
3. Slippage (estimé, paramétrable)

Ne rien changer d'autre à la logique existante (règles d'entrée à l'Open de D, ordre intra-jour SL/TP, gaps SL_GAP/TP_GAP, budget `capital_engage`, tirage aléatoire seedé, etc.).

## Avant de coder

[ ] Lire entièrement `knn_backtest.py` et `knn_backtest_config.json`. Ne rien supposer sur leur contenu : repérer les endroits exacts où (a) le pool de candidats est constitué, (b) les entrées sont exécutées, (c) les sorties sont exécutées (TP, SL, TP_GAP, SL_GAP), (d) le PnL est calculé, (e) les fichiers de sortie sont écrits.
[ ] Si un point est ambigu, choisir l'option la plus simple, la noter dans le résumé final, ne pas poser de question.
[ ] Ne pas inventer de tarifs : les valeurs de frais vont dans le JSON de config avec un commentaire "à vérifier" (voir plus bas).

## Etapes

[ ] **1. Filtre prix plancher**
- Paramètre config : `prix_min` = 9.0 (mettre `null` ou 0 pour désactiver)
- Appliqué **sur le pool de candidats (prediction == 1), avant le tirage aléatoire** du jour
- Prix testé : `Close(D-1)` (la décision est prise à D-1, utiliser `Open(D)` serait du look-ahead)
- Évalué **chaque jour** (un titre peut passer au-dessus ou en dessous de 9 $ au fil du temps), pas une liste figée
- Journaliser dans le `.log` : nombre de candidats avant/après filtre, moyenne sur la période

[ ] **2. Frais de transaction (aller et retour)**
- Nombre d'actions = `floor(montant_du_lot / prix_entree)` (entier, comme en réel)
- Calculer les frais à l'entrée ET à la sortie, sur ce nombre d'actions
- Modèle IBKR Tiered, tous les paramètres dans le JSON (bloc `frais`) :
  - commission par action (départ : 0.0035 $/action)
  - commission minimale par ordre (départ : 0.35 $)
  - commission maximale par ordre en % de la valeur de l'ordre (départ : 1 %)
  - frais de compensation/bourse par action (départ : 0.0002 $/action, à vérifier)
  - frais réglementaires **à la vente uniquement** (SEC fee en $ par million de valeur vendue, FINRA TAF en $ par action vendue avec plafond par ordre) : **chercher les valeurs en vigueur dans la documentation officielle IBKR / SEC / FINRA**, ne pas les deviner ; si introuvables, mettre 0 et le signaler clairement
- Interrupteur `frais.actif` (true/false)
- Fonction dédiée `calc_frais(nb_actions, prix, sens)` (sens = "achat" ou "vente"), testable isolément

[ ] **3. Slippage**
- Le slippage s'applique **sur le prix d'exécution**, en % défavorable (achat plus cher, vente moins chère), un paramètre par type d'exécution dans le JSON (bloc `slippage`) :
  - `entree_open` : achat à l'Open (ordre OPG, enchère d'ouverture) — hypothèse de départ 0.05 %
  - `sortie_tp` : sortie sur ordre limite TP — hypothèse de départ 0 % (une limite ne glisse pas, mais peut ne pas être exécutée : ignoré ici)
  - `sortie_sl` : sortie sur stop (devient un ordre au marché) — hypothèse de départ 0.10 %
  - `sortie_gap` : SL_GAP / TP_GAP exécutés à l'Open — hypothèse de départ 0.10 %
- Ce sont des **hypothèses**, pas des mesures. Les écrire dans le JSON avec la mention "à calibrer avec les fills réels du paper trading (avgFillPrice vs Open)"
- Interrupteur `slippage.actif`
- Le prix d'exécution retenu (après slippage) sert à tous les calculs : nombre d'actions, TP/SL de référence restent calculés sur le prix d'entrée **théorique** (Open) pour ne pas changer les règles

[ ] **4. PnL et sorties**
- Dans `.journal.csv`, pour chaque trade, ajouter les colonnes : `prix_theorique_entree`, `prix_exec_entree`, `prix_theorique_sortie`, `prix_exec_sortie`, `nb_actions`, `frais_entree`, `frais_sortie`, `slippage_cout` ($, entrée + sortie), `pnl_brut` (sans frais ni slippage), `pnl_net`
- `.summary.csv` et `.log` : afficher côte à côte **PnL brut / PnL après slippage / PnL net**, total des frais, total du slippage, frais moyens par trade en % du lot, nombre de trades
- `.equity.csv` : la courbe d'equity doit être en **net**
- Les positions encore ouvertes en fin de test restent annulées à PnL 0 (règle actuelle) — ne pas y toucher

[ ] **5. Non-régression (obligatoire)**
- Avec `prix_min` = null, `frais.actif` = false et `slippage.actif` = false, le backtest doit redonner **exactement** les mêmes trades et le même PnL que la version actuelle (même seed 42). Le vérifier en lançant d'abord la version d'origine (copie sauvegardée `knn_backtest_avant_frais.py`) puis la nouvelle, et comparer les journaux
- Puis lancer 4 scénarios et les mettre dans un tableau comparatif dans le résumé : (a) tout désactivé, (b) filtre seul, (c) filtre + frais, (d) filtre + frais + slippage

## Détails

#### Conventions
- Ne pas modifier le fichier d'origine avant d'en avoir fait une copie `knn_backtest_avant_frais.py` à côté
- Code simple, commenté en français, pas de refactorisation ni de réécriture de ce qui fonctionne
- Tous les nouveaux paramètres dans `knn_backtest_config.json`, aucune valeur en dur dans le code
- Si le fichier d'entrée ou une colonne attendue manque, s'arrêter avec un message clair

#### Fin de travail : vérifier avant de conclure
- [ ] Les 3 interrupteurs fonctionnent (désactivés = résultat identique à l'ancien)
- [ ] Un trade pris au hasard a été recalculé à la main dans le résumé (prix, nb actions, frais, slippage, PnL net) pour prouver que les formules sont justes
- [ ] Les nouvelles colonnes sont bien présentes dans le journal
- [ ] Résumé final **court** : tableau des 4 scénarios, hypothèses retenues, points ambigus rencontrés, valeurs de frais laissées à vérifier

#### Remarque
Utiliser les variables d'environnement dans .envrc pour les chemins, comme le reste du projet. Ne rien exécuter d'autre que le backtest et la comparaison demandée.
