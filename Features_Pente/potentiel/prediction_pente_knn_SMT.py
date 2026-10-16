import pandas as pd
import numpy as np
from sklearn import preprocessing
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix

def main():
    # kNN with SMOTE (Synthetic Minority Over-sampling Technique) to handle imbalanced data.
    # This version creates synthetic examples of the minority class.

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

    print(f"--- Rééquilibrage des classes (SMOTE) ---")
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    print(f"Nouveau volume d'entraînement (SMOTE) : {len(X_train_resampled)} lignes\n")

    print(f"--- Prétraitement (StandardScaler) ---")
    scaler = preprocessing.StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_resampled)
    X_test_scaled = scaler.transform(X_test)
    print("Scaling terminé.\n")

    print(f"--- Optimisation du paramètre k (GridSearchCV) ---")
    knn = KNeighborsClassifier()
    param_grid = {'n_neighbors': range(1, 26)}
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
