# Charte de documentation — Trading System

*Créé le 18/08/2026*

## Objectif

Documentation professionnelle et complète du système de trading, produite étape par étape et composant par composant — depuis la création des fichiers de référence des tickers jusqu'au paper trading.

## Méthode

1. Pour chaque composant/étape, un prompt structuré est généré (par Claude, dans la conversation de travail).
2. Ce prompt est donné à une IA de génération de documents pour produire un **PDF couleur simple**, professionnel et clair.
3. Chaque PDF respecte la charte graphique ci-dessous.

## Charte graphique

### Polices

| Usage | Police | Repli si indisponible |
|---|---|---|
| Titre | Segoe UI | équivalent le plus proche |
| Sous-titre / info principale | Arial | équivalent le plus proche |
| Élément saillant / outline | Georgia | équivalent le plus proche |
| Texte courant | Police carrée type Arial, taille normale | équivalent le plus proche |

### Couleurs

**Texte ordinaire** : noir

**Tableaux avec titre** (dégradé, du plus soutenu au plus clair) :
- `#D64327`
- `#DF664E` (+ caractères blancs)
- `#E68875`
- `#EDA99C`
- `#F4CBC3`
- `#FBECE9`

**Encadrés, outlines, références** (dégradé, du plus soutenu au plus clair) :
- `#4E9BDF` (+ caractères blancs)
- `#75B1E6`
- `#9CC7ED`
- `#C3DDF4`
- `#E9F3FB`

## Idées pour plus tard (hors périmètre immédiat)

- **Tableau de bord quotidien** : petite appli avec un écran affichant les étapes du jour (planifié / en cours / en erreur / terminé) et un résumé des résultats de chaque étape, pour éviter de parcourir tous les logs.
- **Journal de trading** : pour revenir sur les décisions passées et faire une analyse régulière de la situation.

## Prochaine étape

Mise en place d'IBKR (TWS/Gateway + connexion au compte démo), avec documentation de cette étape produite en parallèle de sa mise en œuvre.
