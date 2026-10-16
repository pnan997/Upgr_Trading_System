# Plan d'implantation : Classificateur kNN pour les Features de Pente

## Objectif
Implémenter un classificateur k-Nearest Neighbors (kNN) pour prédire la colonne `target` à partir des features calculées (`T`, `Q`, `M`, `A`, `N`), en utilisant le jeu de données d'entraînement pour l'apprentissage et le jeu de test pour l'évaluation.

## Étapes de l'implémentation

### 1. Chargement des données
- Charger `train_features.csv` et `test_features.csv`.
- Séparer les colonnes de caractéristiques (Features: `T, Q, M, A, N`) de la cible (`target`).

### 2. Prétraitement (Preprocessing)
- **Mise à l'échelle (Scaling)** : Le kNN étant basé sur des distances euclidiennes, il est impératif de normaliser ou standardiser les données pour que chaque feature ait un poids équivalent. Nous utiliserons `StandardScaler` de `scikit-learn`.
- *Note* : Il faudra calculer la moyenne et l'écart-type sur le jeu d'entraînement uniquement, puis appliquer cette transformation au jeu de test pour éviter le "data leakage".

### 3. Entraînement du modèle
- Utiliser `KNeighborsClassifier` de `scikit-learn`.
- Définir une stratégie pour choisir le meilleur paramètre $k$ (nombre de voisins).

### 4. Optimisation des hyperparamètres (Turing)
- Utiliser `GridSearchCV` sur le jeu d'entraînement pour trouver la valeur optimale de $k$ (par exemple, tester les valeurs de 1 à 20).

### 5. Évaluation du modèle
- Prédire les étiquettes sur le jeu de test (`test_features.csv`).
- Calculer et afficher les métriques de performance suivantes :
    - **Accuracy** (Précision globale)
    - **Precision** (Capacité à ne pas prédire un positif par erreur)
    - **Recall** (Capacité à trouver tous les positifs)
    - **F1-Score** (Moyenne harmonique entre précision et recall, crucial si les classes sont déséquilibrées)

### 6. Sortie des résultats
- Afficher un rapport de classification complet (`classification_report`).
- Optionnel : Afficher une matrice de confusion pour visualiser les erreurs de prédiction.
