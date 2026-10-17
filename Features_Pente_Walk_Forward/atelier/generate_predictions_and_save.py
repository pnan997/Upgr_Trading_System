import pandas as pd
import numpy as np
from sklearn import preprocessing
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GridSearchCV
import os

def main():
    # kNN with SMOTE (Synthetic Minority Over-sampling Technique) to handle imbalanced data.
    base_path = os.path.join(os.environ["TS_ROOT"], "Features_Pente_Walk_Forward")
    train_path  = os.environ.get("WF_TRAIN_PATH",  f'{base_path}/train_features.csv')
    test_path   = os.environ.get("WF_TEST_PATH",   f'{base_path}/test_features.csv')
    output_path = os.environ.get("WF_PRED_OUT",    f'{base_path}/test_features_with_predictions.csv')

    print(f"--- Chargement des données ---")
    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)
    print(f"Train: {len(df_train)} lignes, Test: {len(df_test)} lignes\n")

    features = ['T', 'Q', 'M', 'A', 'N']
    X_train = df_train[features]
    y_train = df_train['target']
    X_test = df_test[features]

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
    grid_search = GridSearchCV(knn, param_grid, cv=5, scoring='f1', n_jobs=-1)
    grid_search.fit(X_train_scaled, y_train_resampled)

    print(f"Meilleur k trouvé : {grid_search.best_params_['n_neighbors']}\n")

    print(f"--- Évaluation et Sauvegarde ---")
    best_knn = grid_search.best_estimator_
    y_pred = best_knn.predict(X_test_scaled)

    # Add predictions to the test dataframe
    df_test_with_preds = df_test.copy()
    df_test_with_preds['prediction'] = y_pred

    print(f"Sauvegarde des résultats dans {output_path}")
    df_test_with_preds.to_csv(output_path, index=False)
    print("Terminé.\n")

if __name__ == '__main__':
    main()
