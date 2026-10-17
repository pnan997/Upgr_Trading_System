# Walk-forward : les 4 programmes enchaînés, section après section

---

## But et moyens (langage python)

Refaire le walk-forward avec les 4 programmes **existants**, dans cet ordre, pour chaque section, puis passer à la section suivante jusqu'à épuisement des données :

1. `generate_training_dataset.py` (features, séparation train / test)
2. `generate_predictions_and_save.py` (entraînement sur le train, prédictions sur le test)
3. `enrich_predictions.py`
4. `knn_backtest.py` (config actuelle : filtre 9 $, frais et slippage déjà implémentés)

Travailler dans `Upgr_Trading_System/Features_Pente_Walk_Forward/atelier/`. Code simple et lisible : l'utilisateur doit comprendre les calculs. Aucune initiative : pas d'étude en plus, pas de contrôle non demandé. Ne pas modifier la logique des 4 programmes. Ne pas écraser les anciens fichiers.

Faire un programme `walk_forward.py` qui calcule les dates de chaque section, puis lance les 4 programmes l'un après l'autre. S'il faut un tout petit changement pour donner les dates et le dossier de sortie à un programme (paramètre ou fichier de config), le faire sans changer ses résultats et le mentionner.

## Avant de coder

[ ] Lire les 4 programmes et leurs fichiers de config
[ ] En cas de point ambigu, choisir l'option la plus simple et la noter dans le résumé, sans poser de question

## Découpage (jours de bourse, sur la liste triée des dates de la base)

Paramètres dans `walk_forward_config.json` :
- `train_jours` = 252 (1 an)
- `gap_jours` = 10
- `test_jours` = 61
- `pas_jours` = 61

Le premier train commence à la première date de la base + 60 jours de bourse (le slope 60 a besoin de 60 jours d'historique). Section k : 252 jours de train, 10 jours d'écart, 61 jours de test ; la section suivante démarre 61 jours plus tard. La dernière section peut être tronquée à la fin de la base.

## Etapes

Pour chaque section k :
[ ] Lancer les 4 programmes dans l'ordre, avec les dates de la section. Les fichiers de la section vont dans `wf_sections/sectionXX_<debut_test>_<fin_test>/`
[ ] Si le programme est interrompu, ne pas refaire les sections terminées
[ ] Ajouter une ligne à `walk_forward_resume.csv` : section, dates train, dates test, nombre de trades, PnL brut, PnL net, retour %, win rate, max drawdown, frais, slippage

À la fin :
[ ] Un `walk_forward_resume.md` court avec le tableau des sections et le total

## Fin de travail
- [ ] Toutes les sections ont tourné jusqu'au bout
- [ ] Résumé **court** : le tableau et les points ambigus rencontrés, sans interprétation

#### Remarque
Utiliser les variables d'environnement de `.envrc` pour les chemins et la base DuckDB.
