# launchd — fiche de référence

## 1. Le concept, en une phrase

`launchd` est le "cron" natif macOS, mais qui gère aussi le démarrage des
applications et des services système. Il ne lit **jamais** ton shell (`.zshrc`,
`.envrc`, `direnv`) : chaque job tourne dans un environnement quasi-vide, isolé.
C'est la source de 90% des surprises quand on vient de cron.

| Notion cron              | Équivalent launchd                              |
|---------------------------|--------------------------------------------------|
| une ligne dans crontab     | un fichier `.plist` (XML) dans `~/Library/LaunchAgents/` |
| `crontab -e`               | créer/éditer le `.plist` à la main               |
| `crontab -l`                | `launchctl list \| grep <nom>` ou `launchctl print gui/$(id -u)/<label>` |
| la tâche est active dès l'édition | il faut *recharger* le job après chaque modif (`bootout` + `bootstrap`) |
| `VAR=valeur commande`       | bloc `EnvironmentVariables` dans le plist        |
| `>> log 2>&1`               | clés `StandardOutPath` / `StandardErrorPath`     |

**Point le plus important à retenir : un `.plist` modifié n'est jamais repris
à chaud.** Il faut explicitement décharger puis recharger le job.

## 2. Anatomie d'un plist (les clés qui comptent vraiment)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pnan9.tradingsystem.download</string>   <!-- identifiant unique du job -->

    <key>ProgramArguments</key>
    <array>
        <string>/chemin/vers/python</string>              <!-- argv[0] : l'exécutable -->
        <string>/chemin/vers/script.py</string>            <!-- argv[1], argv[2]... -->
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/pnan9/Trading_System</string>          <!-- equiv. cd avant la commande -->

    <key>EnvironmentVariables</key>
    <dict>
        <key>TS_ROOT</key>
        <string>/Users/pnan9/Trading_System</string>       <!-- ce que .envrc t'offrait gratuitement -->
    </dict>

    <key>StartCalendarInterval</key>                       <!-- equiv. "45 17 * * 2-6" -->
    <array>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>0</integer></dict>
        <!-- un dict par jour, pas de notation "2-6" : il faut lister chaque jour -->
    </array>

    <key>StandardOutPath</key>
    <string>/chemin/vers/log.log</string>                  <!-- equiv. >> log -->
    <key>StandardErrorPath</key>
    <string>/chemin/vers/log.log</string>                  <!-- equiv. 2>&1 -->

    <key>RunAtLoad</key>
    <false/>                                               <!-- true = lance aussi au chargement du job -->
</dict>
</plist>
```

Pièges fréquents :
- **Pas de "2-6"** : `StartCalendarInterval` n'accepte pas les plages, un `<dict>` par jour.
- **Pas de shell implicite** : `ProgramArguments` appelle l'exécutable directement, pas de `&&`, `|`, `~` — si le script a besoin d'un shell, le premier élément doit être `/bin/zsh` (ou bash) et le script en argument.
- **`PATH` minimal** : launchd tourne avec `/usr/bin:/bin:/usr/sbin:/sbin`. Toute commande externe (`git`, `duckdb` CLI...) doit être en chemin absolu ou `PATH` doit être rallongé dans `EnvironmentVariables`.

## 3. Les 4 commandes à connaître (et rien que ça)

```bash
# Charger un job pour la première fois
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/mon-job.plist

# Décharger un job (à faire AVANT tout rechargement après une modif du plist)
launchctl bootout gui/$(id -u)/com.pnan9.tradingsystem.mon-job

# Lancer un job tout de suite, sans attendre l'horaire (pour tester)
# -k force le démarrage même si launchd pense le job déjà dans un état
# actif/récent -- plus fiable que `start` juste après un bootout/bootstrap,
# où `start` peut rester muet sans rien dire (constaté le 22/09).
launchctl kickstart -k gui/$(id -u)/com.pnan9.tradingsystem.mon-job

# Variante héritée, existe aussi mais attend le label NU, jamais un chemin
# domaine/service (gui/501/... ne marchera pas avec start) :
launchctl start com.pnan9.tradingsystem.mon-job

# Voir l'état d'un job : en cours ? dernier code de sortie ? erreur ?
launchctl print gui/$(id -u)/com.pnan9.tradingsystem.mon-job
```

**Règle d'or après une modif de plist :**
```bash
launchctl bootout gui/$(id -u)/com.pnan9.tradingsystem.mon-job
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/mon-job.plist
```
Jamais l'un sans l'autre (relancer `bootstrap` seul sur un job déjà chargé donne
souvent l'erreur "Input/output error" — cf. section pannes).

Pour lire `print` sans se noyer dans 3 pages, isoler l'essentiel :
```bash
launchctl print gui/$(id -u)/com.pnan9.tradingsystem.mon-job | grep -E "state|last exit|runs ="
```

## 4. Pannes classiques : symptôme → cause → remède

| Symptôme                                              | Cause probable                                   | Remède                                                                 |
|--------------------------------------------------------|---------------------------------------------------|--------------------------------------------------------------------------|
| `Bootstrap failed: 5: Input/output error`               | Le job est déjà chargé (tu as modifié le plist sans `bootout` avant) | `bootout` puis `bootstrap`                                              |
| `Bootstrap failed: 5: Input/output error` (même après bootout) | Fichier plist invalide (XML cassé) ou attribut de quarantaine (fichier téléchargé au navigateur) | `plutil -lint fichier.plist` (doit dire `OK`) puis `xattr -d com.apple.quarantine fichier.plist` |
| Job tourne (`last exit code = 0`) mais rien ne se passe | Le script attend une variable d'env non définie (ex. `TS_DATA_DIR`) et échoue silencieusement en interne, ou une commande externe introuvable (`PATH` minimal) | Ajouter les variables manquantes dans `EnvironmentVariables` ; tester le script à la main avec les mêmes variables pour isoler le problème |
| Aucun fichier de log créé du tout                        | Le job n'a jamais été exécuté (mauvais label, jamais bootstrappé, ou bootout fait par erreur) | `launchctl print gui/$(id -u)/<label>` — si "Could not find service", le job n'existe pas dans launchd, il faut le (re)charger |
| `last exit code` différent de 0                          | Le script a planté (chemin faux, permission, erreur Python) | Lancer le script à la main hors launchd, avec les mêmes variables d'environnement — l'erreur sera lisible dans le terminal au lieu d'être noyée |
| `last exit reason = OS_REASON_CODESIGNING` (`runs = 1`, process tué quasi instantanément, avant même `minimum runtime`) | Le binaire cible de `ProgramArguments` (souvent un interpréteur Python installé via Homebrew, signé "ad-hoc") a été remplacé depuis le dernier chargement du job — macOS/AMFI invalide la signature qu'il avait en mémoire pour ce chemin dès que le fichier change (ex. `brew upgrade`, lien `.venv/bin/python` réparé) | Re-signer le binaire réel (pas le lien) : `codesign --force --sign - "$(readlink -f /chemin/vers/python)"`, puis recharger le job entièrement (`bootout` + `bootstrap`, pas un simple `kickstart`) — à refaire à chaque fois que le binaire change |

## 5. Méthode de diagnostic (dans cet ordre, à chaque souci)

1. `launchctl print gui/$(id -u)/<label>` → le job existe-t-il, tourne-t-il, quel exit code ?
2. `plutil -lint <plist>` → le fichier est-il un XML valide ?
3. `xattr -l <plist>` et `<script>` → quarantaine à retirer ?
4. Lancer le script/commande **à la main**, dans le terminal, avec les mêmes variables d'env que le plist → isole "problème launchd" vs "problème script".
5. Vérifier le fichier de log correspondant → vide (le job tourne mais le script ne produit rien) ou absent (le job n'a jamais tourné) ne racontent pas la même histoire.

## 6. Où vivent les fichiers

- Jobs utilisateur : `~/Library/LaunchAgents/*.plist`
- Rotation des logs (natif macOS, pas besoin de coder une purge) : `/etc/newsyslog.d/*.conf`