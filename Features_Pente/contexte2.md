# Contexte de Backtesting - Phase 2

## État actuel
- Fichier de prédictions : `/app/working/workspaces/FinCodeur95/duckdb/Features_Pente/test_features_with_predictions.csv` (contient `date`, `symbol`, `T`, `Q`, `M`, `A`, `N`, `target`, `prediction`).
- Problème : Manque les prix (`open`, `high`, `low`, `close`) pour le backtest.

## Règles de Backtest actualisées
- **Signal d'achat** : Si `prediction == 1` à la clôture du jour $J$, l'achat est effectué au jour $J+1$.
- **Sortie (Profit ou SL)** : Peut survenir dès le jour de l'achat ($J+1$) si :
    - Profit cible (+1%) : `High >= Prix_Achat * 1.01` ou `Close >= Prix_Achat * 1.01`.
    - Stop Loss (SL) : `Low <= Prix_Achat * (1 - SL_percent)` ou `Close <= Prix_Achat * (1 - SL_percent)`.

## Prochaines étapes
1. Enrichir le CSV avec les prix (`open`, `high`, `low`, `close`) de chaque jour pour chaque symbole.
2. Implémenter le moteur de backtest.

## Notes : 
Ne pas confondre le host et le docker! la liste est détaillée dans le prompt système. Les fichiers qui commencent par /app ont toutes les chances d'être des fichiers SUR LE DOCKER.
De même, quand on parle de copaw, on parle du nom du conteneur sur le docker. 
On a une base de données. Il est peut-être judicieux de l'exploiter en tant que telle plutôt que de décharger systématiquement les tables dans des fichiers .csv. Voir si ça se justifie.
