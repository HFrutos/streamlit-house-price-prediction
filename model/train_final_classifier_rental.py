#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ML Pipeline Part 3: Train Final Rental Property Classifier

This script takes the best hyperparameters found by the Optuna study,
trains a final LightGBM model on the full dataset, evaluates its performance,
and saves the final model artifact for deployment.
"""

# Standard library imports
from pathlib import Path
import json
import pickle
import warnings

# Third-party library imports
import pandas as pd
import numpy as np
import lightgbm as lgb
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Suppress specific warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)


# --- Configuration Constants ---

# --- Path Configuration ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "model" / "artifacts"

# --- File Configuration ---
# Inputs for this script
CLUSTERED_DATA_FILENAME = "rental_properties_clustered.csv"
BEST_PARAMS_FILENAME = "rental_best_classifier_params.json"
INPUT_DATA_FILEPATH = PROCESSED_DATA_DIR / CLUSTERED_DATA_FILENAME
INPUT_PARAMS_FILEPATH = ARTIFACTS_DIR / BEST_PARAMS_FILENAME

# Outputs of this script
CLASSIFIER_FILENAME = "rental_property_classifier.pkl"
FINAL_FEATURES_FILENAME = "rental_classifier_features.json"

# --- Main Functions ---

def load_data_and_params(data_path, params_path):
    """Loads the clustered dataset and the best hyperparameters."""
    print("--- 1. Loading Data and Hyperparameters ---")
    
    # Load clustered data
    if not data_path.exists():
        print(f"FATAL ERROR: Clustered data file not found at {data_path}")
        return None, None
    try:
        df = pd.read_csv(data_path)
        print("Clustered data loaded successfully.")
    except Exception as e:
        print(f"FATAL ERROR: An error occurred while loading the data: {e}")
        return None, None

    # Load best hyperparameters
    if not params_path.exists():
        print(f"FATAL ERROR: Hyperparameters file not found at {params_path}")
        return None, None
    try:
        with open(params_path, 'r') as f:
            best_params = json.load(f)
        print("Best hyperparameters loaded successfully.")
    except Exception as e:
        print(f"FATAL ERROR: An error occurred while loading parameters: {e}")
        return None, None
        
    return df, best_params

def display_and_save_confusion_matrix(y_true, y_pred, labels, title, output_filepath):
    """
    Calculates, prints a text version, and saves a graphical Plotly
    confusion matrix as an HTML file.
    """
    # --- Text Version ---
    print(f"\n--- {title} ---")
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm,
                         index=[f"True: {label}" for label in labels],
                         columns=[f"Pred: {label}" for label in labels])
    print(cm_df)

    # --- Graphical Version ---
    fig = go.Figure(data=go.Heatmap(
        z=cm,
        x=[str(l) for l in labels],
        y=[str(l) for l in labels],
        colorscale='Blues',
        text=cm, texttemplate="%{text}"
    ))
    fig.update_layout(
        title=title,
        xaxis_title='Predicted Label',
        yaxis_title='True Label',
        xaxis_type='category', # Treat labels as categories
        yaxis_type='category'
    )

    try:
        # Save the plot as an interactive HTML file
        fig.write_html(output_filepath)
        print(f"\nGraphical confusion matrix saved to: {output_filepath}")
    except Exception as e:
        print(f"Could not save confusion matrix plot: {e}")


# --- Main Execution Block ---
if __name__ == "__main__":
    df, best_params = load_data_and_params(INPUT_DATA_FILEPATH, INPUT_PARAMS_FILEPATH)

    if df is not None and best_params is not None:
        # --- Prepare Data ---
        print("\n--- 2. Preparing Data for Final Training ---")
        
        y = df['cluster']
        X = df.drop(columns=[
            'price_eur_pm', 'barrio_encoded', 
            'cluster_label', 'cluster'
        ], errors='ignore')

        cols_to_drop = [
            'price_eur_pm', 
            'barrio_encoded', 
            'cluster_label', # Text version of original cluster
        ]

        # Convert categorical features to the 'category' dtype for LightGBM
        categorical_features = ['barrio', 'distrito']
        for col in categorical_features:
            if col in X.columns:
                X[col] = X[col].astype('category')
        print("Data prepared. X shape: {}, y shape: {}".format(X.shape, y.shape))

        # --- Split Data for Final Evaluation ---
        # We create one final train/test split to validate our final model's performance.
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print("\n--- 3. Data Split for Final Evaluation ---")
        print(f"Training set size: {len(X_train)}")
        print(f"Test set size: {len(X_test)}")

        # --- Train an Initial Model for Evaluation ---
        print("\n--- 4. Training and Evaluating Model on Test Set ---")
        eval_model = lgb.LGBMClassifier(random_state=42, verbosity=-1, **best_params)
        eval_model.fit(X_train, y_train)
        
        y_pred_test = eval_model.predict(X_test)
        
        print("\n--- Final Model Performance on Held-Out Test Set ---")
        print(f"Accuracy: {accuracy_score(y_test, y_pred_test):.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred_test))
        
        # Define the output path for the plot
        cm_filename = "rental_classifier_confusion_matrix.html"
        cm_filepath = ARTIFACTS_DIR.parent / "reports" / "figures" / cm_filename
        
        # Ensure the directory exists
        (ARTIFACTS_DIR.parent / "reports" / "figures").mkdir(parents=True, exist_ok=True)
        
        # Generate and save the confusion matrix to visually assess model performance
        display_and_save_confusion_matrix(
            y_test, 
            y_pred_test, 
            labels=sorted(y_test.unique()), 
            title="Confusion Matrix on Test Set",
            output_filepath=cm_filepath
        )

        # --- Re-train Final Model on 100% of Data ---
        print("\n--- 5. Re-training Final Model on All Available Data ---")
        # For the model we deploy, we want it to learn from all available data.
        # We re-train it on the full X and y DataFrames using the same best parameters.
        final_model = lgb.LGBMClassifier(random_state=42, verbosity=-1, **best_params)
        final_model.fit(X, y)
        print("Final model trained on all data successfully.")

        # --- Save Final Artifacts ---
        print("\n--- 6. Saving Final Model and Feature List ---")
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save the trained classifier
        with open(ARTIFACTS_DIR / CLASSIFIER_FILENAME, 'wb') as f:
            pickle.dump(final_model, f)
        print(f"Final classifier saved to: {ARTIFACTS_DIR / CLASSIFIER_FILENAME}")

        # Save the list of features the model was trained on
        # This is crucial for ensuring new data has the same columns in the same order
        final_features_dict = {'features': X.columns.tolist()}
        with open(ARTIFACTS_DIR / FINAL_FEATURES_FILENAME, 'w') as f:
            json.dump(final_features_dict, f, indent=4)
        print(f"Final feature list saved to: {ARTIFACTS_DIR / FINAL_FEATURES_FILENAME}")

        print("\n--- Classifier Training Pipeline Complete ---")