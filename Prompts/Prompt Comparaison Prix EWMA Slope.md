# Comparaison cours, moyenne et slope

---

## But et moyens (langage python)

Faire une fonction externe (cp_PriceEMASlope(ticker) à inclure dans un programme.

Faire un programme de test qui appelle cette fonction avec le ticker AAPL

Lancer le programme de test 

## Etapes de cp_PriceEMASlope(`ticker`)


[ ] Après vérificaction de l'existence, chargement  de la table duckdb (ohlcv_`ticker`) -> df 

[ ] Calcul de l'EWMA(60) et de la droite de régression entre les mêmes points

[ ] Affichage du cours, de la pente et de l'EWMA(60)

[ ] Export du graphique dans fichier `TS_GFX_DIR`/`ticker`_PxEMASlp.png

## Détails

#### Couleurs
- Fond "#eeeeee"
- Cours "#c7d132"
- Slope "#32d1ce"
- Moyenne "#cfe3e3"
- Si cours > moyenne, remplissage entre les 2 "#349c17"
- Si cours < moyenne, remplissage entre les 2 "#b83d18"

#### Légende
- Titre : "Comparaison EWMA60 et cours + Slope"
- Cartouche en bas à droite
- Légende de chaque courbe avec un trait de chaque couleur. Largeur (interne) Taille de la légende la plus grande + 5px de chaque côté
- Fond "#ffffff"
- Rectangle arrondi. Bord 2px  : "#4a291f"

#### **Remarque**
Utiliser les variables d'environnement dans .envrc