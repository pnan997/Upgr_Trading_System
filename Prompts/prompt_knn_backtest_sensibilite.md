# Backtest KNN : contrôle pnl_brut, sensibilité au slippage, bruit du tirage, TP/SL alternatifs

---

## But et moyens (langage python)

Le backtest `Upgr_Trading_System/Features_Pente_Walk_Forward/atelier/knn_backtest.py` gère désormais filtre prix, frais et slippage. Il faut maintenant savoir **si le résultat net est robuste**, sans modifier la logique de trading.

Faire un programme d'étude séparé `etude_sensibilite.py` (dans le même dossier) qui **importe / appelle** les fonctions de `knn_backtest.py` plutôt que de les recopier. Si le backtest n'est pas appelable proprement en tant que fonction avec une config en paramètre, faire le **minimum** de refactorisation pour le permettre (sans changer les résultats), et le dire dans le résumé.

Ne pas modifier les règles de trading. Ne pas toucher à `knn_backtest_avant_frais.py`.

## Avant de coder

[ ] Relire `knn_backtest.py` et `knn_backtest_config.json` tels qu'ils sont maintenant

[ ] Si un point est ambigu, prendre l'option la plus simple et la noter dans le résumé, sans poser de question

## Etapes

[ ] **1. Contrôle de cohérence pnl_brut**
- Constat : dans l'ancien run, `pnl_brut` du scénario filtre+frais+slippage (11 684,81) diffère de celui filtre+frais (11 685,72), alors qu'il devrait être identique
- Trouver la cause (probablement : le nombre d'actions est calculé sur le prix après slippage, donc l'arrondi change) et dire si c'est voulu
- Définir clairement et documenter dans le code : `pnl_brut` = PnL aux prix théoriques avec **le même nombre d'actions** que le trade réel. Corriger le calcul si ce n'est pas le cas. Les anciens scénarios (a) et (b) doivent rester identiques

[ ] **2. Grille de sensibilité au slippage** (seed 42, filtre 9 $ et frais actifs)
- `slippage.entree_open` ∈ {0 %, 0,025 %, 0,05 %, 0,10 %}
- `slippage.sortie_sl` et `slippage.sortie_gap` (même valeur) ∈ {0 %, 0,05 %, 0,10 %, 0,20 %}
- `sortie_tp` reste à 0 %
- Sortie : tableau 4×4 du **PnL net** et tableau 4×4 du **retour en %**, écrits dans `etude_sensibilite.md` et dans un CSV
- Repérer et écrire dans le résumé la frontière où le PnL net passe sous 0 (le seuil de rentabilité compte plus que la valeur centrale)

[ ] **3. Bruit du tirage aléatoire** (slippage à la valeur actuelle de la config)
- Pour seeds ∈ {42, 43, 44, 45, 46} : lancer (a) tout désactivé et (b) filtre 9 $ seul, puis (d) filtre + frais + slippage
- Tableau : PnL net par seed, moyenne, écart-type, pour chaque scénario
- Conclusion explicite : l'écart entre (a) et (b) est-il supérieur au bruit entre seeds, oui ou non ? Ne pas conclure plus que ce que les chiffres permettent

[ ] **4. TP/SL alternatifs** (seed 42, filtre + frais + slippage actuels)
- Variantes (TP / SL) : 1,5 % / 0,6 % (référence), 2,5 % / 1,0 %, 4,0 % / 2,0 %
- Tableau : trades, win rate, PnL brut, frais, slippage, PnL net, retour %
- Les paramètres de ces variantes passent par la config (pas de valeur en dur) ; ne pas changer la règle « pas d'achat si Open(D) ≥ Close(D-1) × (1+TP) »

## Détails

- Chaque exécution du backtest doit être indépendante (pas de fichier de sortie écrasé entre deux runs : écrire dans un sous-dossier `etude_sensibilite_runs/<nom_du_run>/`, ou désactiver l'écriture des journaux détaillés pendant la grille et ne garder que le résumé)
- Afficher un compteur de progression simple (n / total) dans la console
- Si un run dure plus de 2 minutes, le signaler dans le résumé avec le temps mesuré
- Non-régression : avec la config actuelle, le run de référence doit redonner exactement 714 trades et PnL net 6 710,56 (scénario d) ; vérifier avant la grille

#### Fin de travail : vérifier avant de conclure
- [ ] Non-régression sur le run de référence (714 trades, 6 710,56 net)
- [ ] La cause de l'écart pnl_brut est expliquée
- [ ] Les 3 tableaux (grille slippage, seeds, TP/SL) sont dans `etude_sensibilite.md`
- [ ] Résumé final **court** : seuil de rentabilité du slippage, verdict sur le bruit du filtre 9 $, meilleure variante TP/SL (avec prudence : une seule période)

#### Remarque
Utiliser les variables d'environnement dans .envrc pour les chemins. Ne rien exécuter d'autre que les études demandées.
