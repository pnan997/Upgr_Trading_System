# Étude de sensibilité — backtest kNN v5

Généré le 2026-10-16 08:38:02.

Config de référence : `knn_backtest_config.json` (seed 42, tp_pct 0.015, sl_pct 0.006, prix_min 9.0, frais.actif True, slippage.actif True).

## Etape 1 — Contrôle pnl_brut (run de référence)

| Contrôle | Valeur |
|---|---|
| Max écart par trade : pnl_brut vs N×(P_tho_sortie−P_tho_entrée) (tolérance ±0.02) | 0.0000 |
| Nombre de trades hors tolérance ±0.02 | 0 |
| Max écart par trade : brut−slippage−frais vs pnl_eur (arrondi par trade) | 0.0050 |
| Somme pnl_brut | 11 678.35 |
| Somme (pnl_eur + slippage_cout + frais_entree + frais_sortie) | 11 678.27 |
| Écart total (somme brut − somme recomposée) | 0.0846 |

Verdict global : **OK** (714 trades contrôlés).

**Note — définition de pnl_brut (v5)** : pnl_brut = PnL aux prix théoriques avec le **même nombre d'actions** que le trade réel, soit `N × (prix_théorique_sortie − prix_théorique_entrée)`.

L'ancien écart (11684.81 vs 11685.72) venait du nombre d'actions calculé sur le prix **après** slippage (arrondi floor différent), combiné à un pnl_brut recalculé via `S = N × entry_exec`.

## Etape 2 — Grille slippage (16 runs)

Config : filtre prix_min 9.0 actif, frais actifs, slippage actif, seed 42, sortie_tp = 0.0. Lignes = entree_open, colonnes = sortie_sl (= sortie_gap).

### pnl_net (EUR)

| entree_open \ sortie_sl | 0.0 | 0.0005 | 0.001 | 0.002 |
|---|---|---|---|---|
| 0.0 | 10 605.57 | 9 530.78 | 8 616.17 | 6 621.78 |
| 0.00025 | 9 883.58 | 8 808.90 | 7 894.45 | 5 900.30 |
| 0.0005 | 8 699.04 | 7 624.78 | 6 710.56 | 4 717.10 |
| 0.001 | 7 082.27 | 6 008.50 | 5 094.84 | 3 102.36 |

### retour_pct (%)

| entree_open \ sortie_sl | 0.0 | 0.0005 | 0.001 | 0.002 |
|---|---|---|---|---|
| 0.0 | 35.35 | 31.77 | 28.72 | 22.07 |
| 0.00025 | 32.94 | 29.36 | 26.31 | 19.66 |
| 0.0005 | 28.99 | 25.41 | 22.37 | 15.72 |
| 0.001 | 23.60 | 20.02 | 16.98 | 10.34 |

### Frontière de rentabilité

Aucune combinaison négative sur la grille explorée.

Plus grande combinaison encore positive (max entree_open+sortie_sl) : entree_open=0.001, sortie_sl/gap=0.002 → pnl_net = 3 102.36 EUR (retour 10.34%).

## Etape 3 — Bruit du tirage (15 runs)

Slippage = valeur actuelle de la config (entree_open 0.0005, sortie_sl 0.001, sortie_gap 0.001, sortie_tp 0). Chiffres seuls, pas de conclusion.

| Seed | (a) tout désactivé | (b) filtre seul | (d) référence |
|---|---|---|---|
| 42 | 11 317.24 | 11 685.72 | 6 710.56 |
| 43 | 11 069.24 | 8 844.73 | 4 046.62 |
| 44 | 10 947.28 | 8 751.90 | 3 679.42 |
| 45 | 9 242.28 | 11 328.95 | 6 435.68 |
| 46 | 9 527.17 | 10 972.53 | 5 505.69 |
| **moyenne** | **10 420.64** | **10 316.77** | **5 275.59** |
| **écart-type (ddof=1)** | **960.31** | **1409.28** | **1370.77** |

## Etape 4 — TP/SL alternatifs (3 runs)

Seed 42, config de référence (filtre + frais + slippage actuels). Variantes uniquement via cfg (tp_pct / sl_pct).

| tp_pct | sl_pct | n_trades | win_rate_pct | pnl_brut | frais | slippage | pnl_net | retour_pct |
|---|---|---|---|---|---|---|---|---|
| 0.015 | 0.006 | 714 | 44.26 | 11 678.35 | 1 079.50 | 3 888.21 | 6 710.56 | 22.37 |
| 0.025 | 0.01 | 548 | 39.23 | 10 239.46 | 859.12 | 3 151.95 | 6 228.35 | 20.75 |
| 0.04 | 0.02 | 282 | 38.65 | 4 951.24 | 449.35 | 1 669.32 | 2 832.56 | 9.43 |

## Temps d'exécution

| Étape | Durée (s) |
|---|---|
| etape0_non_regression | 8.6 |
| etape1_controle_pnl_brut | 0.0 |
| etape2_grille_slippage | 139.7 |
| etape3_bruit_seeds | 134.8 |
| etape4_tpsl | 26.7 |
| **Total** | **310.3** |

Un temps par run > 120 s est à surveiller (5 étape(s), cf. console pour le détail par run).
