# Règles de Backtesting — Phase 4 (Version Opérationnelle)

Supercède `contexte3.md`. Ce document est la référence unique du moteur
`knn_backtest.py` (v3, 2026-06-15).

---

## I. Environnement technique

| Composant | Détail |
|:---|:---|
| Container | `copaw` (Docker, Ubuntu) |
| Script | `/app/working/workspaces/FinCodeur95/duckdb/Features_Pente/atelier/knn_backtest.py` |
| Config | `atelier/knn_backtest_config.json` (tous les paramètres métier) |
| Source données | `Features_Pente/test_features_with_predictions_ohlcv.csv` |
| Sorties | `Features_Pente/knn_backtest.{log,journal,summary,equity}.csv` |
| Colonnes OHLCV | `date, symbol, Open, High, Low, Close` (CamelCase) + `prediction` |
| Univers | ~3 025 symboles NYSE/NASDAQ, 295 jours de bourse |
| Prédictions | 483 481 signaux `prediction=1` sur 859 633 lignes |

---

## II. Paramètres (knn_backtest_config.json)

| Clé JSON | Valeur par défaut | Description |
|:---|:---|:---|
| `capital_initial` | 30 000 € | Dotation totale du compte |
| `capital_engage` | 15 000 € | Budget journalier max (voir §III.1) |
| `tp_pct` | 0.010 (1,0 %) | Take Profit relatif au prix d'entrée |
| `sl_pct` | 0.006 (0,6 %) | Stop Loss relatif au prix d'entrée |
| `plafond_lot` | 5 000 € | Taille max par trade |
| `seuil_minimal` | 2 500 € | En dessous : aucun nouveau trade |
| `seed` | 42 | Graine RNG (reproductibilité) |

> Modifier le JSON uniquement. Le script ne contient aucun paramètre métier codé en dur.

---

## III. Logique de simulation

### III.1 Gestion du capital — `capital_engage` (budget journalier)

`capital_engage` est un **budget journalier non recyclable** :

```
budget_restant_jour_D = capital_engage
                      - existing_exposure   ← positions ouvertes des jours PASSÉS
                      - daily_deployed      ← capital ouvert AUJOURD'HUI (cumulé)
```

- `existing_exposure` est figé **avant** toute entrée ou sortie du jour.
- `daily_deployed` s'accumule à chaque ouverture de position (same-day ou multi-jours).
- Une position fermée le jour même **ne libère pas** de budget pour une autre position le même jour.

**Conséquence pratique** : avec `capital_engage = 15 000` et `plafond_lot = 5 000`,
on ouvre au maximum **3 positions par jour**, indépendamment du nombre de signaux.

**Pourquoi pas `current_exposure` recalculé à chaque itération ?**
En v2, `current_exposure` retombait à 0 après chaque clôture same-day, permettant
de recycler le capital 6-7 fois par jour (29 800 € déployés pour un engage de 15 000).
Le `daily_deployed` corrige ce contournement.

### III.2 Cycle de liquidité

```
(A)  liquid_cash += pending_cash    ← cash des clôtures de la VEILLE
     pending_cash = 0

(C)  Nouvelles entrées              ← signaux de D-1, exécution à Open(D)
     → liquid_cash  -= S
     → daily_deployed += S
     → check sortie same-day → pending_cash += S ± PnL

(B)  Clôtures des positions multi-jours (jours PASSÉS uniquement)
     → pending_cash += size ± PnL

(D)  Instantané équité
     total_equity = liquid_cash + pending_cash + market_value
```

> `pending_cash` est inclus dans `total_equity` : l'argent en transit (clôtures
> du jour non encore réglées) fait partie de la valeur réelle du portefeuille.
> Sans cette inclusion, l'equity chutait artificiellement de ~15 000 € chaque jour.

### III.3 Entrées (signaux D → exécution D+1)

1. **Signal** : `prediction = 1` au jour D.
2. **Entrée** : `Open(D+1)`.
3. **Filtre gap-up** : si `Open(D+1) >= Close(D) × (1 + tp_pct)` → trade annulé
   (le marché a déjà dépassé la cible pendant la nuit).
4. **Taille** :
   - `T = min(plafond_lot, liquid_cash, budget_restant_jour)`
   - `N = floor(T / price)` unités entières
   - `S = N × price` (taille réelle)
   - Si `S < seuil_minimal` → trade annulé
5. **Sélection** : ordre aléatoire reproductible (`seed + day_idx` par jour)
   parmi tous les candidats de la veille.

### III.4 Sorties

#### a) Sortie same-day (holding_days = 0)
Vérifiée immédiatement après l'entrée, sur les H/L du jour d'entrée.

#### b) Sortie multi-jours — règle d'ordre intra-journalier

```
dist_down = |Low  - Open|
dist_up   = |High - Open|

si dist_down > dist_up :   # prix a davantage baissé
    vérifier SL en premier, puis TP
sinon :                    # prix a davantage monté (ou égal)
    vérifier TP en premier, puis SL
```

Prix d'exécution : `SL_price` ou `TP_price` (pas le Low/High brut).

#### c) Gap à l'ouverture — positions multi-jours uniquement

| Situation | Condition | Exécution | Raison journal |
|:---|:---|:---|:---|
| Gap-down (défavorable) | `Open[Dx] <= SL_price` | `Open[Dx]` (< SL) | `SL_GAP` |
| *(Gap-up favorable)* | *(voir §IV.1)* | *(Open[Dx])* | *(TP_GAP)* |

> Le gap-down est réaliste : l'ordre SL ne peut pas s'exécuter à un prix
> inférieur à l'ouverture, donc on subit le slippage complet.

### III.5 Fin de backtest

Les positions encore ouvertes à la dernière date sont annulées au **prix d'achat**
(PnL = 0). Elles sont listées dans le log et comptées dans `n_positions_ouvertes_fin`.

---

## IV. Évolutions planifiées

### IV.1 Gap-up en TP (priorité : mineure)

**Symétrique du gap-down.** Si une position multi-jours ouvre **au-dessus du prix TP**
(`Open[Dx] >= TP_price`), l'objectif est atteint dès l'ouverture.
Exécution au prix `Open[Dx]` (potentiellement > TP — slippage favorable).

```python
# À ajouter dans (B), avant resolve_exit :
if open_val is not None and open_val >= pos["tp_price"]:
    exit_price = round(open_val, 2)
    reason     = "TP_GAP"
elif open_val is not None and open_val <= pos["sl_price"]:
    exit_price = round(open_val, 2)
    reason     = "SL_GAP"
else:
    exit_price, reason = resolve_exit(...)
```

**Impact attendu** : peu de trades affectés (gap-up ≥ 1 % en une nuit reste rare
sur des actions non-event), PnL légèrement amélioré sur ces cas.

---

## V. Métriques de sortie (summary.csv)

| Métrique | Définition |
|:---|:---|
| `capital_initial` / `capital_engage_max` | Paramètres de configuration |
| `capital_final` | `total_equity` au dernier jour |
| `pnl_total` | `capital_final - capital_initial` |
| `retour_pct` | `pnl_total / capital_initial × 100` |
| `n_trades` | Total trades clôturés (same-day + multi-jours) |
| `win_rate_pct` | % trades avec `pnl_eur > 0` |
| `gain_moyen` / `perte_moyenne` | PnL moyen sur les trades gagnants / perdants |
| `ratio_gain_perte` | `sum_gains / abs(sum_losses)` |
| `esperance_par_trade` | `wr × gain_moyen + (1-wr) × perte_moyenne` |
| `duree_{moyenne,mediane,max}_jours` | Holding period |
| `n_same_day` / `n_multi_day` | Décomposition par type |
| `pnl_same_day` / `pnl_multi_day` | PnL par type |
| `n_sl_gap` / `pnl_sl_gap` | Trades avec gap-down |
| `max_perte_journaliere_eur` | **Drawdown opérationnel** : pire `daily_pnl` négatif sur une journée |
| `max_drawdown_cumul_eur` | Drawdown standard peak-to-trough (pour référence) |

> **`max_perte_journaliere_eur`** est la métrique de risque principale.
> Avec 3 positions × 5 000 € × SL 0,6 % = 90 € nominal.
> Les cas `SL_GAP` peuvent porter ce chiffre à quelques centaines d'euros.

---

## VI. Résultats de référence (run du 2026-06-15, seed=42)

| Métrique | Valeur |
|:---|:---|
| Capital final | 35 993 € |
| PnL total | +5 993 € (+20,0 %) |
| Trades | 780 (741 same-day, 39 multi-jours) |
| Win rate | 47,4 % |
| Espérance / trade | +7,68 € |
| SL_GAP | 5 occurrences |
| **Perte max journalière** | **218 €** |
| Drawdown cumul (réf.) | 552 € |

---

## VII. Archivage des résultats précédents 

- Création d'un nouveau sous-répertoire : ** historique_ résultats **
>Les sorties des runs précédents y sont manuellement renommés et transférés pour laisser la place à de nouveaux résultats en fonction des tests et modifications ultérieurs
>Pour l'instant, ils contiennent le run du 15/06 (suffixe \_15\_06\_1.csv) et le run avec prise en compte du gap_TP (suffixe \_15\_06\_2.csv) 
