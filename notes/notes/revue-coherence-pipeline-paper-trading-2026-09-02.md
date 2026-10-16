# Revue de cohérence — Pipeline de paper trading IBKR

*Rapport du 02/09/2026 — lecture seule, aucun code modifié.*
*Périmètre : `run_daily_pipeline.py` + ses dépendances + `ibkr_paper_trade.py`.*

Références de fichiers : dossier racine = `Paper_Trading/atelier/`. Les lignes citées
sont à lire dans ces fichiers (ex. `run_daily_pipeline.py:159`).

---

## 0. Verdict en une phrase

Le pipeline est **cohérent et robuste dans sa logique de trading** (garde-fous,
principe *fail-loud*, anti-recyclage de capital, annulation des fills orphelins).
Il y a **un seul vrai bug** (archivage des runs anciens = perte de données
silencieuse) et quelques **nettoyages d'hygiène** (étiquette obsolète, clés de
config mortes, copies obsolètes). Rien ne bloque le trading à ce jour.

| Gravité | Nombre |
|---|---|
| 🔴 Bug (données) | 1 |
| 🟡 Incohérence / config morte | 4 |
| 🟠 Bug latent | 1 |
| 🔵 Hygiène | 2 |

---

## 1. Où ça se trouve

Tout vit dans `Paper_Trading/atelier/` :

| Rôle | Fichier |
|---|---|
| Orchestrateur quotidien | `run_daily_pipeline.py` |
| Exécuteur IBKR | `ibkr_paper_trade.py` |
| Config commune | `paper_trading_config.json` |
| Décision de re-entraînement (importé) | `retrain_scheduler.py` |
| Étapes du pipeline (appelées en subprocess) | `build_features.py`, `retrain_scheduled.py`, `predict_daily.py`, `enrich_predictions.py` |
| Planification (templates) | `com.pnan9.tradingsystem.paper.{pipeline,ibkr}.plist.template` |

⚠️ **Copies obsolètes** dans le même dossier, non référencées par le code actif :
`ibkr_paper_trade.save.py`, `ibkr_paper_trade copy.py`,
`run_daily_pipeline_Old_V1.py`, `run_daily_pipeline_Old_V2.py`,
`com.pnan9.tradingsystem.paper.{pipeline,ibkr}_Old_V1.plist.template`.
Source de confusion ; à archiver ou à supprimer (suppression uniquement sur demande).

---

## 2. Ce que ça fait

### `run_daily_pipeline.py` (lanceur quotidien, via LaunchAgent)
Exécute en chaîne dans `Paper_Trading/Data/run_YYYYmmdd_HHMMSS/` :

1. **build_features.py** → lit `tickers_meta.db` (tables `ohlcv_*`), calcule les 5
   features pente `T,Q,M,A,N` + target, split train/test → `train_features.csv`,
   `test_features.csv`.
2. **retrain_scheduler.check_retrain_due()** → décide si un re-entraînement est dû
   (cadence **61 jours de bourse NYSE**, état dans `Paper_Trading/retrain_state.json`).
3. **retrain_scheduled.py** *(seulement si dû)* → SMOTE + StandardScaler +
   GridSearchCV sur KNN, sauvegarde `.joblib` + mise à jour de l'état.
4. **predict_daily.py** → charge le modèle figé, prédit →
   `test_features_with_predictions.csv`.
5. **enrich_predictions.py** → jointure OHLCV du jour →
   `test_features_with_predictions_ohlcv.csv`.
6. Sélection des candidats (dernier jour, `prediction==1`, tri `Q,M,T` desc,
   top 20) → `prepared_orders_*.csv` + `latest_prepared_orders.csv`.
7. Écrit `manifest.json` de fin de run (`status: ok/failed`).

Design **fail-loud** : calendrier illisible, état corrompu, modèle absent →
exception, jamais de décision par défaut.

### `ibkr_paper_trade.py` (exécuté après le pipeline)
Lit `latest_prepared_orders.csv` puis :

- **Garde-fou de fraîcheur** (`ensure_fresh_pipeline_success`, lignes 128–163) :
  refuse de trader si le run le plus récent n'a pas `status:ok` **ou** ne date pas
  d'aujourd'hui — compense l'absence de dépendance entre jobs launchd.
- **Garde-fou OPG** (`ensure_before_opg_cutoff`, lignes 92–126) : refuse si week-end,
  jour férié NYSE, ou trop tard pour l'enchère d'ouverture (coupure effective
  9 h 25 ET = 9 h 28 − marge 180 s).
- **Capital engagé vs exposition réelle** (`current_exposure` sur `ib.positions()`,
  lignes 181–193, 248–250) : anti-recyclage du capital (même bug déjà corrigé dans
  `knn_backtest.py`).
- Soumet les achats en **ordre OPG**, pose un **bracket TP/SL en OCA**
  (`place_exit_oca`, lignes 218–230), **annule l'achat non rempli**
  (lignes 342–344), log la **dérive de cash** (non bloquante, lignes 366–380).
- **Dry-run par défaut** ; `--transmit` pour passer les ordres réels.

---

## 3. Ce qui est cohérent (points positifs)

- ✅ **Flux bout-à-bout propre** : chaque étape produit le fichier que la suivante
  consomme ; tous les fichiers actifs compilent sans erreur.
- ✅ **Corrections du 09/08** (exposées dans le docstring de `ibkr_paper_trade.py`)
  implémentées **et cohérentes** entre elles : exposition réelle (n°1), dérive de
  cash en log (n°2), `continue` plutôt que `break` (n°3), annulation + calendrier
  NYSE (n°4) — toutes alignées sur la décision du 08/08 « la sélection continue
  avec les autres tickers ».
- ✅ **Garde-fou de fraîcheur** (n°5) bien conçu : compense proprement le manque de
  dépendance entre jobs, bloque tout trading sur une base périmée ou en échec.
- ✅ **Ordre de sauvegarde / état correct** : `record_retrain_success` n'est appelé
  qu'après la sauvegarde des `.joblib` ; `predict_daily` exige le modèle ; le
  re-échec d'une étape marque le run `failed` et bloque l'étape IBKR.
- ✅ **`check_retrain_due`** strict (lève `RetrainSchedulerError` plutôt que
  deviner) — cohérent avec la philosophie fail-loud.
- ✅ **Sécurité** : dry-run par défaut, coupures OPG explicites, garde-fou de
  fraîcheur, anti-recyclage. Aucun passage ne risque d'acheter sur une base douteuse.

---

## 4. Points à corriger

### 🔴 1. Archivage des runs anciens : perte de données silencieuse  ☐

**Où** : `run_daily_pipeline.py:77-95` (`compress_old_files`).
**Problème** : l'archivage s'appuie **uniquement sur le nom de fichier**
(`archive/<nom>.gz`). Or chaque dossier `run_*/` contient les **mêmes noms**
(`manifest.json`, `train_features.csv`, `test_features.csv`,
`test_features_with_predictions.csv`,
`test_features_with_predictions_ohlcv.csv`). Dès que **deux** runs franchissent le
seuil de 21 jours, **le plus récent écrase l'archive du précédent** : l'archive ne
conserve en réalité que le *dernier* run passé, tout le reste est perdu
silencieusement. De plus, les dossiers `run_*/` vidés restent (l'archivage ne
supprime que les fichiers, pas les dossiers vides).
**Conséquence** : contredit le docstring du pipeline (« les anciens fichiers de plus
de 3 semaines sont compressés en .gz » → préservation). Non bloquant pour le
trading, mais l'archivage est factuellement inutile au-delà du dernier run.
**Statut** : **latent mais imminent** — au 02/09 seul `run_20260728` a déjà 21 j ;
`run_20260818` et suivants franchissent le seuil dans ~6 jours, l'écrasement se
produit au premier passage.
**Correction suggérée** : archiver avec un chemin unique par run,
`archive/<run_name>/<fichier>.gz`, et vider/supprimer les dossiers `run_*/` une fois
archivés.

### 🟡 2. `entry_rule` dément le comportement réel  ☐

**Où** : `run_daily_pipeline.py:159`.
**Problème** : `prepared_orders` reçoit
`entry_rule = "MKT at market open + 60s after cash refresh"`, alors que l'exécuteur
passe désormais des ordres **OPG** (prix d'ouverture, décision du 25/08), pas un MKT
60 s après l'ouverture. L'étiquette inscrite dans le CSV **ment sur l'action
réelle** — piégeux si quelqu'un lit les orders.
**Correction suggérée** : aligner la valeur sur le comportement OPG, ex.
`"OPG (open-price) at 09:30 ET, submitted before 09:25 ET cutoff"`.

### 🟡 3. Trois clés de config mortes  ☐

Confirmé par grep : utilisées **uniquement** dans les variantes `.save`/`.copy`, pas
dans le code actif (`paper_trading_config.json`) :

| Clé | Ligne config | Statut |
|---|---|---|
| `entry_after_open_seconds` | 42 | morte (remplacée par la logique OPG) |
| `cash_wait_timeout_seconds` | 43 | morte (correction n°2 du 09/08) |
| `dry_run_default` | 45 | morte (le dry-run est contrôlé par le flag CLI `--transmit`) |

**Correction suggérée** : supprimer ces clés, ou les lire réellement.

### 🟡 4. Env `TS_DATA_DIR` posée mais jamais lue  ☐

**Où** : `run_daily_pipeline.py:211` (et dans les templates plist).
**Problème** : la variable est posée pour les subprocess, mais aucun script enfant ne
la lit — ils déduisent le dossier depuis `TS_ROOT` + `Paper_Trading/Data`.
**Correction suggérée** : soit la supprimer, soit la faire lire par les enfants.

### 🟠 5. Crash latent si prix de référence manquant  ☐

**Où** : `ibkr_paper_trade.py:296-298`.
**Problème** : si `marketPrice()` est indisponible **et** que `signal_close` est NaN
(Close absent dans l'enrichissement), `ref_price` devient NaN et
`int(notional // ref_price)` lève `ValueError`. Peu probable (data dispo à 9 h),
mais non protégé.
**Correction suggérée** : `if math.isnan(ref_price) or ref_price <= 0: continue`
(saut du candidat, cohérent avec le principe de poursuite).

---

## 5. Notes d'hygiène / à vérifier

### 🔵 6. Template plist décalé de l'agent installé
Les templates `*.plist.template` portent `StartCalendarInterval` Weekday **2–6**
(mar–sam). L'**agent réellement installé** tourne en Weekday **1–5 = lundi–vendredi**
(*confirmé par `launchctl print gui/$(id -u)/com.pnan9.tradingsystem.*`*), ce qui
est le bon calendrier de trading. Le planning est donc **correct côté exécution** ;
seul le **template est obsolète** et doit être recopié avant tout redéploiement.
→ *Aucune action sur le code.*

### 🔵 7. Heuristique `make_contract`
`ibkr_paper_trade.py:208` remplace `_` par ` ` (`UHAL_B` → `UHAL B`), correct pour
les suffixes B/A-shares. Attention si un symbole contenait un `_` signifiant autre
chose. À confirmer sur la liste de tickers, sinon sans risque.

---

## Statut global (à cocher quand corrigé)

- [ ] 🔴 1 — Archivage unique par run + nettoyage des `run_*/` vides
- [ ] 🟡 2 — `entry_rule` aligné OPG
- [ ] 🟡 3 — Suppression des 3 clés de config mortes
- [ ] 🟡 4 — `TS_DATA_DIR` lue ou supprimée
- [ ] 🟠 5 — Garde NaN sur `ref_price`
- [ ] 🔵 6 — Template plist recopié à l'agent installé (1–5)
- [ ] 🔵 7 — Vérif de l'heuristique `_`→` `

*On en reste là pour le moment (02/09) : rapport posé, aucune modification du code.*
