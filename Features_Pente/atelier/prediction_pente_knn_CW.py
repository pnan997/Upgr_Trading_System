# kNN with Class Weights (Oversampling) to handle imbalanced data.
# This version balances classes by duplicating minority samples.

import pandas as pd
import numpy as np
from sklearn import preprocessing
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix

def main():
    base_path = os.path.join(os.environ["TS_ROOT"], "Features_Pente")
    train_path = f'{base_path}/train_features.csv'
    test_path = f'{base_path}/test_features.csv'

    print(f"--- Chargement des données ---")
    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)
    print(f"Train: {len(df_train)} lignes, Test: {len(df_test)} lignes\n")

    features = ['T', 'Q', 'M', 'A', 'N']
    X_train = df_train[features]
    y_train = df_train['target']
    X_test = df_test[features]
    y_test = df_test['target']

    # --- Étape de Rééquilibrage (Oversampling) ---
    print(f"--- Rééquilibrage des classes (Oversampling du '0') ---")
    df_minority = df_train[df_train['target'] == 0]
    n_majority = len(df_train[df_train['target'] == 1])
    n_minority = len(df_minority)
    diff = n_majority - n_minority
    
    if diff > 0:
        print(f"Ajout de {diff} échantillons de la classe 0...")
        df_oversampled = pd.concat([df_train, df_minority.sample(n=diff, replace=True)], ignore_index=True)
    else:
        df_oversampled = df_train

    X_train_resampled = df_oversampled[features]
    y_train_resampled = df_oversampled['target']
    print(f"Nouveau volume d'entraînement : {len(df_oversampled)} lignes\n")

    print(f"--- Prétraitement (StandardScaler) ---")
    scaler = preprocessing.StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_resampled)
    X_test_scaled = scaler.transform(X_test)
    print("Scaling terminé.\n")

    print(f"--- Optimisation du paramètre k (GridSearchCV) ---")
    knn = KNeighborsClassifier()
    param_grid = {'n_neighbors': range(1, 26)}
    # On utilise F1 pour la sélection car on veut un équilibre entre précision et rappel
    grid_search = GridSearchCV(knn, param_grid, cv=5, scoring='f1')
    grid_search.fit(X_train_scaled, y_train_resampled)

    print(f"Meilleur k trouvé : {grid_search.best_params_['n_neighbors']}")
    print(f"Meilleur score de validation (F1) : {grid_search.best_score_:.4f}\n")

    print(f"--- Évaluation sur le jeu de TEST ---")
    best_knn = grid_search.best_estimator_
    y_pred = best_knn.predict(X_test_scaled)

    print("Rapport de classification :")
    print(classification_report(y_test, y_pred))

    print("Matrice de confusion :")
    print(confusion_matrix(y_test, y_pred))

if __name__ == '__main__':
    main()
