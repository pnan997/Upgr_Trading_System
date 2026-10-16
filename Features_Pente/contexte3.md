# Règles de Backtesting - Phase 3 (Version Carrée)

Ce document définit la structure mathématique et opérationnelle du moteur de backtest pour garantir un réalisme strict, notamment sur la gestion de la liquidité.

## I. Gestion du Capital (Money Management)

Le pilier central est la distinction entre la valeur totale du compte et l'argent réellement disponible pour trader.

*   **Capital Initial ($C_{init}$)** : $15\,000$ €.
*   **Cash Disponible ($R$)** : Liquidité réelle (cash) prête à être déployée pour de nouveaux trades.
*   **Equity ($E$)** : Valeur totale du compte, calculée comme : $E = R + \sum (\text{Valeur des positions ouvertes})$.

### Règles de Taille et de Liquidité
1.  **Calcul de la Taille ($S$)** : Pour chaque nouveau signal détecté, la taille du trade est déterminée par le cash disponible :
    $$ S = \min(5000, R) $$
2.  **Seuil de Sécurité** : Si $R < 2500$, aucun nouveau trade n'est autorisé ($S = 0$).
3.  **Cycle de Liquidité (Update du Cash)** : Le cash libéré par un trade clôturé (Capital initial du trade + PnL réalisé) est considéré comme disponible pour de nouveaux trades le **lendemain matin**. Cela garantit qu'on ne réinvestit pas de l'argent qui est encore "en transit".

## II. Logique d'Exécution (Execution)

### 1. Entrée (Entry)
*   **Signal** : Détecté au jour $D$.
*   **Action** : Achat au prix `Open` du jour $D+1$.
*   **Filtre de Sécurité** : Si le prix d'ouverture `Open(D+1)` est supérieur ou égal au prix cible `TP_price`, l'opportunité est annulée (le marché a déjà trop monté).

### 2. Sortie (Exit)
*   **Condition** : Un trade est clôturé dès que son prix atteint la cible définie ($TP$ ou $SL$).
*   **Type de sortie** :
    *   **Take Profit (TP)** : $+1,0\%$ du prix d'entrée.
    *   **Stop Loss (SL)** : $-0,6\%$ du prix d'entrée.

## III. Paramètres Fixes

| Paramètre | Valeur |
| :--- | :--- |
| Capital de départ | $30\,000$ \$ |
| Taille cible max | $5\,000$ \$ |
| Seuil de stop trading | $2\,500$ \$ (Cash disponible) |
| Take Profit (TP) | $+1,0\%$ |
| Stop Loss (SL) | $-0,6\%$ |
