# 🍳 Fiche-cuisine Git & GitHub

> Aide-mémoire des commandes, fichiers de configuration et bonnes pratiques Git/GitHub.

---

## 1. Les ingrédients de base (vocabulaire)

| Terme | Ce que c'est |
|---|---|
| **Dépôt (repo)** | Ton projet, avec tout son historique |
| **Commit** | Une photo de ton projet à un instant T |
| **Branche** | Une ligne de développement (ex: `main`, `feature-x`) |
| **Remote / origin** | La version distante sur GitHub |
| **Push** | Envoyer tes commits locaux → GitHub |
| **Pull** | Récupérer les commits GitHub → local |
| **Clone** | Copier un repo distant en local |
| **HEAD** | Le commit sur lequel tu es actuellement |
| **Upstream** | La branche distante associée à ta branche locale |

---

## 2. Le cycle quotidien (recette de base)

```bash
# Vérifier où on en est
git status

# Voir ce qu'on a modifié
git diff

# Ajouter les fichiers modifiés
git add .                    # tout
git add fichier.txt          # un seul
git add dossier/             # un dossier

# Enregistrer un commit
git commit -m "message clair et concis"

# Envoyer vers GitHub
git push

# Récupérer les nouveautés distantes
git pull
```

**Le réflexe minimal :** `add` → `commit` → `push`. Toujours dans cet ordre.

---

## 3. Les commandes de secours (les épices)

### Voir l'historique

```bash
git log --oneline --graph --all   # vue compacte et visuelle
git log -5                        # les 5 derniers commits
git log -- fichier.txt            # historique d'un fichier précis
```

### Annuler / corriger

```bash
git restore fichier.txt           # annule les modifs non commitées d'un fichier
git restore --staged fichier.txt  # retire du staging (sans perdre les modifs)
git commit --amend                # corrige le dernier commit (message ou contenu)
git reset --soft HEAD~1           # annule le dernier commit, garde les modifs
git reset --hard HEAD~1           # ⚠️ annule le dernier commit ET les modifs
```

### Branches

```bash
git branch                        # liste les branches locales
git branch -a                     # toutes (locales + distantes)
git switch ma-branche             # changer de branche
git switch -c nouvelle-branche    # créer et basculer
git merge ma-branche              # fusionner dans la branche courante
git branch -d ma-branche          # supprimer (si fusionnée)
git branch -D ma-branche          # supprimer de force
```

### Remotes

```bash
git remote -v                     # voir les remotes
git remote add origin URL         # ajouter un remote
git remote set-url origin URL     # changer l'URL
git remote remove origin          # supprimer
```

### Récupérer / pousser

```bash
git fetch                         # récupère sans fusionner
git pull                          # fetch + merge
git push                          # pousse
git push -u origin main           # 1ʳᵉ fois : lie la branche au upstream
git push --force-with-lease       # force, mais sécurité si divergence
```

### Situation courante : "push rejected"

```bash
git pull                          # récupérer et fusionner
# résoudre les conflits éventuels dans les fichiers
git add .
git commit
git push
```

---

## 4. Les fichiers de configuration importants

### `.gitignore` — la liste de courses (ce qu'on ne veut PAS versionner)

Placé à la racine du repo. Un motif par ligne.

```gitignore
# Dossiers
__pycache__/
.venv/
node_modules/

# Fichiers
*.log
*.db
*.bak
.env

# Gros fichiers de données
*.csv
*.csv.gz
*.joblib
*.h5

# Dossiers spécifiques
Paper_Trading/Data/archive/
Paper_Trading/model/

# Fichiers OS
.DS_Store
Thumbs.db
```

**Règles de syntaxe :**

- `dossier/` → ignore tout un dossier
- `*.ext` → tous les fichiers avec cette extension
- `!fichier.txt` → exception (ne pas ignorer)
- `chemin/**/fichier` → à n'importe quelle profondeur
- `#` → commentaire

⚠️ **Piège classique :** un `.gitignore` n'agit que sur les fichiers **non encore suivis**. Si un fichier est déjà dans l'historique, il faut le retirer :

```bash
git rm --cached fichier.txt      # retire du suivi mais garde le fichier local
git rm -r --cached dossier/      # idem pour un dossier
git commit -m "Retrait du suivi"
```

Et si c'est dans l'historique profond (gros fichiers) → `git filter-repo` (voir plus bas).

### `.git/config` — la config locale du repo

Visible avec `git config --list --local`. Contient notamment l'URL du remote et le upstream de chaque branche.

### `~/.gitconfig` — la config globale (tes préférences)

```bash
git config --global user.name "Prénom Nom"
git config --global user.email "email@exemple.com"
git config --global init.defaultBranch main
git config --global core.editor "code --wait"     # VS Code comme éditeur
git config --global pull.rebase false             # pull en merge (par défaut)
```

Modifiable directement avec :

```bash
git config --global --edit
```

---

## 5. Le format d'un message de commit

Un bon message, c'est comme une bonne étiquette :

```
Type: Résumé court à l'impératif (max ~50 caractères)

Corps optionnel qui explique le POURQUOI, pas le COMMENT.
Lignes de ~72 caractères max.

Refs: #123
```

**Types courants :**

- `feat:` nouvelle fonctionnalité
- `fix:` correction de bug
- `docs:` documentation
- `refactor:` réorganisation sans changement fonctionnel
- `chore:` tâches diverses (deps, config)
- `test:` tests

**Exemples :**

```
feat: ajout du calcul de pente sur 20 jours
fix: corrige le décalage horaire dans les features
chore: mise à jour des dépendances
docs: ajout du README sur l'installation
```

---

## 6. Les cas particuliers utiles

### Je veux voir ce qui a changé mais pas encore commité

```bash
git diff                      # modifs non stagées
git diff --staged             # modifs stagées (prêtes à committer)
```

### J'ai oublié un fichier dans le dernier commit

```bash
git add fichier_oublié.txt
git commit --amend --no-edit  # garde le message existant
```

### Je veux annuler un commit déjà poussé

```bash
git revert <hash>             # crée un nouveau commit qui annule l'ancien
                              # (propre, ne réécrit pas l'histoire)
```

### J'ai fait une bêtise irréversible

```bash
git reflog                    # liste TOUTES les actions récentes avec hash
git reset --hard <hash>       # revient à un état antérieur
```

Le `reflog` est ton filet de sécurité : presque rien n'est vraiment perdu.

### Je veux récupérer un fichier d'une autre branche

```bash
git checkout ma-branche -- chemin/fichier.txt
```

### Nettoyer les fichiers non suivis

```bash
git clean -n                  # dry-run : montre ce qui serait supprimé
git clean -fd                 # supprime fichiers et dossiers non suivis
```

---

## 7. GitHub en ligne — points clés

- **Branche par défaut** : `main` (anciennement `master`)
- **Pull Request (PR)** : proposer une fusion de branche, avec revue
- **Issues** : suivi des tâches/bugs
- **Actions** : CI/CD intégré (fichiers dans `.github/workflows/`)
- **Releases** : versions taguées (`git tag v1.0.0 && git push --tags`)
- **Secrets** : variables sensibles stockées dans `Settings → Secrets`

---

## 8. Tableau récapitulatif : "j'ai un problème → je fais quoi"

| Situation | Commande |
|---|---|
| Je veux juste sauvegarder mon travail | `add` → `commit` → `push` |
| Push rejeté (divergence) | `git pull` puis `git push` |
| J'ai commité un truc à jeter | `git reset --soft HEAD~1` |
| J'ai poussé un truc à jeter | `git revert <hash>` |
| Fichier à ne plus suivre | `git rm --cached` + `.gitignore` |
| Gros fichier dans l'historique | `git filter-repo` + `push --force` |
| Remote perdu | `git remote add origin URL` |
| Branche sans upstream | `git push -u origin main` |
| J'ai tout cassé | `git reflog` puis `git reset --hard <hash>` |

---

## 9. VS Code — raccourcis express

| Action | Raccourci / Emplacement |
|---|---|
| Panneau Source Control | `Ctrl+Shift+G` |
| Commit | écrire le message + `Ctrl+Enter` |
| Sync (pull + push) | bouton circulaire en bas à gauche |
| Terminal intégré | `` Ctrl+` `` (backtick) |
| Git Graph (extension) | visualisation graphique de l'historique |

---

## 10. Cas avancé : purger de gros fichiers de l'historique

Utilisé quand un fichier volumineux a été commité par le passé et bloque le push.

**Prérequis :** faire une sauvegarde du dossier local avant toute manipulation.

```bash
# 1. Installer l'outil
pip install git-filter-repo

# 2. Supprimer les chemins de tout l'historique
git filter-repo --path Paper_Trading/model/ --path Paper_Trading/Data/archive/ --invert-paths

# 3. Réattacher le remote (filter-repo le supprime par sécurité)
git remote add origin https://github.com/USER/REPO.git

# 4. Pousser en forçant et lier le upstream
git push --set-upstream origin main --force
```

⚠️ `--force` écrase l'historique distant. À réserver aux dépôts solo ou après concertation avec les collaborateurs.

---

**Règle d'or :** en cas de doute, `git status` d'abord. Ça ne mange pas de pain et ça t'évite 90 % des surprises.