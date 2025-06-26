#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ML Pipeline Part 2a: Hyperparameter Optimization for Sales Classifier

This script uses the clustered property data to find the optimal hyperparameters
for a LightGBM classification model.

The process includes:
1.  Loading the clustered dataset.
2.  Preparing the data (defining features X and target y).
3.  Using Optuna to perform a guided search for the best hyperparameters.
4.  Using Stratified K-Fold Cross-Validation within each trial to get a robust
    performance metric (F1-score).
5.  Printing the best parameters found to the console.
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard library imports
from pathlib import Path
import json
import warnings

# Third-party library imports
import pandas as pd
import numpy as np
import lightgbm as lgb
import optuna
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score


# --- Configuration Constants ---

# --- Path Configuration ---
# This script is located in the `model/` directory.
SCRIPT_DIR = Path(__file__).resolve().parent # -> .../model/
PROJECT_ROOT = SCRIPT_DIR.parent           # -> .../streamlit-house-price-prediction/

PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "model" / "artifacts"

# --- File Configuration ---
# Input file (the output from the clustering script)
INPUT_FILENAME = "sale_properties_clustered.csv"
INPUT_FILEPATH = PROCESSED_DATA_DIR / INPUT_FILENAME
BEST_PARAMS_FILENAME = "sale_best_classifier_params.json"

# --- Optuna Study Constants ---
N_TRIALS = 50 # Number of trials for the search. 50-100 is a good start.

# Suppress Optuna's experimental warning for cleaner output
warnings.filterwarnings("ignore", category=optuna.exceptions.ExperimentalWarning)

# --- Main Data Loading and Preparation Functions ---

def load_clustered_data(filepath):
    """Loads the clustered dataset from a CSV file."""
    print("--- 1. Loading Clustered Data ---")
    print(f"Attempting to load data from: {filepath}")
    if not filepath.exists():
        print(f"FATAL ERROR: Input file not found at {filepath}")
        return None
    try:
        df = pd.read_csv(filepath)
        print("Clustered data loaded successfully.")
        print(f"Dataset shape: {df.shape}")
        return df
    except Exception as e:
        print(f"FATAL ERROR: An error occurred while loading the data: {e}")
        return None

def objective(trial, X, y):
    """
    The objective function for Optuna to optimize.
    It defines the hyperparameter search space, trains a LightGBM model
    using cross-validation, and returns the performance score.

    Args:
        trial (optuna.Trial): An Optuna trial object, used to suggest hyperparameters.
        X (pd.DataFrame): The feature set.
        y (pd.Series): The target variable.

    Returns:
        float: The mean cross-validation score (macro F1-score) for the trial.
    """

    # Get the number of unique classes from the target variable
    num_classes = y.nunique()

    # Define the search space for the hyperparameters we want to tune
    param_grid = {
        "objective": "multiclass",
        "metric": ["multi_logloss", "multi_error"],
        "num_class": num_classes,
        "n_estimators": trial.suggest_int("n_estimators", 200, 1500),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 20, 400),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "random_state": 42,
        "n_jobs": 2,
        "verbosity": -1
    }

    # We use Stratified K-Fold for cross-validation because it maintains the
    # same proportion of each cluster in every fold, which is crucial for imbalanced data.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    scores = []
    # Manually loop through each fold
    for train_idx, val_idx in cv.split(X, y):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # Instantiate the model for this fold
        model = lgb.LGBMClassifier(**param_grid)

        # Explicitly pass the list of categorical feature names to the .fit() method.
        # This ensures LightGBM uses its special handling for these columns.
        model.fit(
            X_train, 
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)]
        )
        
        # Make predictions and calculate the F1 score for this fold
        preds = model.predict(X_val)
        score = f1_score(y_val, preds, average='macro')
        scores.append(score)

    # Return the average F1 score across all folds
    return np.mean(scores)

# --- Main Execution Block ---
if __name__ == "__main__":
    df = load_clustered_data(INPUT_FILEPATH)

    if df is not None:
        # Based on our analysis, Cluster 2 was identified as an anomaly group with only 2 properties.
        # We will remove it before training the classifier.
        print(f"\n--- Pre-filtering Data ---")
        print(f"Original shape before filtering: {df.shape}")
        print("Original cluster distribution:\n", df['cluster'].value_counts())
        
        # Keep all rows where the cluster is NOT 2
        df_filtered = df[df['cluster'] != 2].copy()
        
        print(f"\nFiltered out cluster 2. New shape: {df_filtered.shape}")
        print("New cluster distribution:\n", df_filtered['cluster'].value_counts())
        print("-" * 50)

        # Create a new target column with contiguous labels (0, 1, 2, 3...) for the model
        df_filtered['cluster_target'] = df_filtered['cluster'].astype('category').cat.codes
        
        # Create a mapping dictionary to keep track of the change.
        # This is crucial for interpreting the model's predictions later.
        # Example: {0: 0, 1: 1, 2: 3, 3: 4} -> "New Label 2 corresponds to Original Label 3"
        cluster_relabel_map = dict(enumerate(df_filtered['cluster'].astype('category').cat.categories))
        
        print("\nRe-labeled cluster IDs for the model:")
        print(df_filtered['cluster_target'].value_counts().sort_index())
        print(f"Original-to-New Label Mapping: {cluster_relabel_map}")
        print("-" * 50)

        # --- Feature Selection (Dropping Columns) ---
        print("\n--- 2. Preparing Features and Target for Classification ---")
        
        # We must drop columns that would cause data leakage or are not features.
        # - 'price_eur': The original regression target. The clusters are heavily derived
        #   from it, so including it would be telling the model the answer.
        # - 'barrio_encoded': This feature was created using the mean of 'price_eur',
        #   so it's a direct proxy for price and also constitutes a data leak.
        # - 'cluster_label': This is the text representation of our target, 'cluster'.
        # - 'cluster': The original cluster ID, which is redundant since we have 'cluster_target'.
        cols_to_drop = [
            'price_eur', 
            'barrio_encoded', 
            'cluster_label', # Text version of original cluster
            'cluster'        # Original cluster ID
        ]
        
        df_model_ready = df_filtered.drop(columns=cols_to_drop, errors='ignore')
        print(f"Dropped columns to prevent data leakage: {cols_to_drop}")


        # --- Convert Categorical Features for LightGBM ---
        # LightGBM has a powerful, built-in mechanism for handling categorical features
        # that is more efficient and often more effective than One-Hot Encoding.
        # To use it, we simply convert the respective columns to the 'category' dtype.
        categorical_features = ['barrio', 'distrito']
        for col in categorical_features:
            if col in df_model_ready.columns:
                df_model_ready[col] = df_model_ready[col].astype('category')
        
        print(f"Converted columns to 'category' dtype for LightGBM: {categorical_features}")

        # Define final X and y
        y = df_model_ready['cluster_target']
        X = df_model_ready.drop(columns=['cluster_target'])


        # --- Part 2: Hyperparameter Optimization ---
        print(f"\n--- 3. Starting Hyperparameter Optimization with Optuna ({N_TRIALS} trials) ---")
        
        # Create a study object. We want to 'maximize' the F1-score.
        study = optuna.create_study(direction="maximize")
        
        # Start the optimization process. Optuna will call the 'objective' function 'n_trials' times.
        # Using a lambda function is a clean way to pass our data (X, y) to the objective function.
        study.optimize(
            lambda trial: objective(trial, X, y), 
            n_trials=N_TRIALS,
            show_progress_bar=True # Number of trials. Increase for more thorough search (e.g., 100-200).
        )
        
        # --- Display Results ---
        print("\n--- Optimization Complete ---")
        print(f"Best cross-validation F1-score (macro): {study.best_value:.4f}")

        # Get the dictionary of best parameters from the completed study
        best_params = study.best_params

        print("Best hyperparameters found:")
        # Print parameters in a clean format
        for key, value in study.best_params.items():
            print(f"  '{key}': {value},")
        print("-" * 50)

        print("Saving best parameters to a JSON file...")
        
        # Ensure the artifacts directory exists
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Construct the full path for the output file
        output_filepath = ARTIFACTS_DIR / BEST_PARAMS_FILENAME
        
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(best_params, f, indent=4)
            print(f"Successfully saved best parameters to: {output_filepath}")
        except Exception as e:
            print(f"An error occurred while saving the parameters file: {e}")

        print("\nNext step: Use these parameters to train the final model in the next script.")