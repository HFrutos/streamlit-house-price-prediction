#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ML Pipeline Part 1: Preprocessing and Clustering for Sales Properties

This script creates distinct property clusters from the sales dataset.
The process includes:
1.  Loading processed data from 'data/processed/'.
2.  Applying advanced encoding (Ordinal, Target, One-Hot) and imputation (IterativeImputer).
3.  Scaling all features using StandardScaler.
4.  Applying the K-Means clustering algorithm to group properties based on their features.
5.  Saving all artifacts (encoders, imputer, scaler, cluster model) to the 'model/' directory
    and the final labeled DataFrame to 'data/processed/'.
"""

# Standard library imports
import json
from pathlib import Path
import pickle
import warnings

# Third-party library imports
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer

# Suppress specific FutureWarnings from scikit-learn for cleaner console output
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="sklearn.cluster._kmeans"
)

# --- Configuration Constants ---

# --- Path Configuration ---
# This script is located in the `model/` directory.
SCRIPT_DIR = Path(__file__).resolve().parent # -> .../model/
PROJECT_ROOT = SCRIPT_DIR.parent           # -> .../streamlit-house-price-prediction/

PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
ARTIFACTS_DIR = PROJECT_ROOT / "model" / "artifacts"

# --- File Configuration ---
# Input file (the result of the data cleaning script)
INPUT_FILENAME = "madrid_sale_properties_processed_1.csv"
INPUT_FILEPATH = PROCESSED_DATA_DIR / INPUT_FILENAME

# Output files for this script
CLUSTERED_DATA_FILENAME = "sale_properties_clustered.csv"
ENCODERS_FILENAME = "sale_encoding_maps.json"
SCALER_FILENAME = "sale_scaler.pkl"
IMPUTER_FILENAME = "sale_iterative_imputer.pkl"
KMEANS_MODEL_FILENAME = "sale_kmeans_model.pkl"

CLUSTERED_DATA_FILEPATH = PROCESSED_DATA_DIR / CLUSTERED_DATA_FILENAME

# --- Modeling & Preprocessing Constants ---
NAN_DROP_THRESHOLD = 0.5 # Drop columns with more than 50% missing values
# Based on elbow plot analysis from the exploratory notebook, 5 was chosen.
OPTIMAL_K = 5


# --- Main Data Loading and Processing Functions ---

def load_data(filepath):
    """Loads the processed dataset from a CSV file."""
    print("--- 1. Loading Data ---")
    print(f"Attempting to load data from: {filepath}")
    if not filepath.exists():
        print(f"FATAL ERROR: Input file not found at {filepath}")
        return None
    try:
        df = pd.read_csv(filepath)
        print("Data loaded successfully.")
        print(f"Initial dataset shape: {df.shape}")
        return df
    except Exception as e:
        print(f"FATAL ERROR: An error occurred while loading the data: {e}")
        return None

def preprocess_and_encode(df, target_variable, encoders_filepath, imputer_filepath):
    """
    Performs all preprocessing and encoding steps on the DataFrame.
    Saves the necessary encoders/mappings and the fitted imputer as artifacts.
    """
    print("\n--- 2. Starting Feature Engineering & Preprocessing ---")

    # Step 2a: Drop unnecessary columns
    df.drop(columns=['url', 'property_id', 'scraped_at', 'energy_cert_classification',
                     'description', 'superficie_util', 'orientacion_list'], # <---- CHANGED
            inplace=True, errors='ignore')
    print(f"Dropped identifier and redundant location columns. Shape is now: {df.shape}")

    # Step 2b: Drop columns with a high percentage of missing values
    missing_value_percent = df.isnull().sum() / len(df)
    cols_to_drop_high_nan = missing_value_percent[missing_value_percent > NAN_DROP_THRESHOLD].index
    cols_to_keep_regardless_of_nan = ['amueblado']
    cols_to_drop_high_nan = [col for col in cols_to_drop_high_nan if col not in cols_to_keep_regardless_of_nan]
    
    if cols_to_drop_high_nan:
        df.drop(columns=cols_to_drop_high_nan, inplace=True)
        print(f"Dropped {len(cols_to_drop_high_nan)} columns with >{NAN_DROP_THRESHOLD*100}% missing values: {cols_to_drop_high_nan}")

    # Step 2c: Ordinal Encoding
    mappings = {
        'age_map': {
            'Más de 50 años': 0, 'Entre 30 y 50 años': 1, 'Entre 20 y 30 años': 2,
            'Entre 10 y 20 años': 3, 'Entre 5 y 10 años': 4, 'Menos de 5 años': 5
        },
        'condition_map': {'A reformar': 0, 'En buen estado': 1, 'Reformado': 2, 'A estrenar': 3}
    }
    df['antiguedad'] = df['antiguedad'].map(mappings['age_map'])
    df['conservacion'] = df['conservacion'].map(mappings['condition_map'])

    # Step 2d: Target Encoding for 'barrio'
    print("Applying Target Encoding for 'barrio'...")
    df['barrio'] = df['barrio'].fillna('Desconocido')
    
    barrio_map = df.groupby('barrio')[target_variable].mean()
    df['barrio'] = df['barrio'].map(barrio_map)
    df.rename(columns={'barrio': 'barrio_encoded'}, inplace=True)
    mappings['barrio_target_map'] = barrio_map.to_dict()

    # Step 2e: One-Hot Encoding for 'amueblado'
    print("Applying One-Hot Encoding for 'amueblado'...")
    df = pd.get_dummies(df, columns=['amueblado'], prefix='amueblado', dummy_na=True)

    # Avoid dtype incompatibility warning: Convert boolean columns to integers BEFORE imputation
    for col in df.select_dtypes(include='bool').columns:
        df[col] = df[col].astype(int)
    print("Converted boolean columns to integer type for imputation.")

    # Isolate features for imputation
    feature_cols = df.drop(columns=[target_variable, 'distrito']).columns.tolist() # <---- CHANGED
    features_df = df[feature_cols].copy() # Use .copy() to work on an explicit copy

    # Avoid ValueError from all-NaN columns: Drop any column that is completely empty.
    features_df.dropna(axis=1, how='all', inplace=True)
    
    # Update feature_cols list to reflect any column drops
    feature_cols = features_df.columns.tolist()
    mappings['final_feature_list'] = feature_cols
    
    # Step 2f: Sophisticated Imputation
    print("Applying IterativeImputer for remaining missing values...")
    imputer = IterativeImputer(max_iter=10, random_state=42, verbose=0)
    imputed_features_array = imputer.fit_transform(features_df)
    df_imputed_features = pd.DataFrame(imputed_features_array, columns=feature_cols, index=df.index)
    
    # Update the main DataFrame with the imputed values
    df[feature_cols] = df_imputed_features

    # Step 2g: Save Artifacts
    print("Saving encoders, mappings, and imputer...")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(encoders_filepath, 'w', encoding='utf-8') as f:
        def convert(o):
            if isinstance(o, (np.int64, np.int32)): return int(o)
            if isinstance(o, (np.float64, np.float32)): return float(o)
            raise TypeError
        json.dump(mappings, f, ensure_ascii=False, indent=4, default=convert)
    print(f"Encoders and feature list saved to {encoders_filepath}")

    with open(imputer_filepath, 'wb') as f:
        pickle.dump(imputer, f)
    print(f"Fitted imputer saved to {imputer_filepath}")

    print("Preprocessing and encoding complete.")
    return df, mappings

# --- Main Execution Block ---
if __name__ == "__main__":
    df_sale = load_data(INPUT_FILEPATH)

    if df_sale is not None:
        # Part 1: Preprocessing and Encoding
        df_processed, encoding_mappings = preprocess_and_encode(
            df_sale, 
            target_variable='price_eur',
            encoders_filepath=(ARTIFACTS_DIR / ENCODERS_FILENAME),
            imputer_filepath=(ARTIFACTS_DIR / IMPUTER_FILENAME)
        )

        # Part 2: Feature Scaling
        print("\n--- 3. Scaling Features ---")
        # Define the feature set FOR CLUSTERING. We exclude redundant location features
        # to get more balanced clusters, but we will keep them in the final output CSV.
        features = df_processed.drop(columns=['price_eur', 'distrito', 'latitude', 'longitude']) # <---- CHANGED
        
        # Avoid RuntimeWarning: Identify and remove columns with zero variance BEFORE scaling
        variances = features.var()
        constant_columns = variances[variances == 0].index
        if not constant_columns.empty:
            print(f"Dropping constant columns with zero variance before scaling: {constant_columns.tolist()}")
            features = features.drop(columns=constant_columns)
            # IMPORTANT: Update the final feature list again if constant columns were dropped
            encoding_mappings['final_feature_list'] = features.columns.tolist()
            with open(ARTIFACTS_DIR / ENCODERS_FILENAME, 'w', encoding='utf-8') as f:
                # Re-save the mappings with the updated final feature list
                json.dump(encoding_mappings, f, ensure_ascii=False, indent=4)
        
        # We use StandardScaler because it is more robust to outliers than MinMaxScaler.
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        print("Features scaled successfully.")

        # Save the Scaler artifact
        with open(ARTIFACTS_DIR / SCALER_FILENAME, 'wb') as f:
            pickle.dump(scaler, f)
        print(f"Scaler saved to {ARTIFACTS_DIR / SCALER_FILENAME}")

        # Part 3: K-Means Clustering
        print(f"\n--- 4. Applying K-Means Clustering with k={OPTIMAL_K} ---")
        kmeans = KMeans(n_clusters=OPTIMAL_K, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features_scaled)
        
        df_processed['cluster'] = cluster_labels
        print("Cluster labels assigned to each property.")

        # Save the K-Means Model artifact
        with open(ARTIFACTS_DIR / KMEANS_MODEL_FILENAME, 'wb') as f:
            pickle.dump(kmeans, f)
        print(f"K-Means model saved to {ARTIFACTS_DIR / KMEANS_MODEL_FILENAME}")
        
        # Part 4: Add Descriptive Cluster Labels based on Analysis
        print("\n--- 5. Adding Descriptive Labels to Clusters ---")
        cluster_label_map = {
            0: 'Piso Señorial Clásico', 1: 'Apartamento Estándar', 2: 'Propiedad Singular (Outlier)',
            3: 'Lujo Moderno (Full Equip)', 4: 'Premium Reformado'
        }
        df_processed['cluster_label'] = df_processed['cluster'].map(cluster_label_map)
        print("Descriptive labels added to the DataFrame.")

        # Part 5: Save the Final Clustered DataFrame
        df_processed.to_csv(CLUSTERED_DATA_FILEPATH, index=False)
        print(f"\nFinal clustered data saved to: {CLUSTERED_DATA_FILEPATH}")

        # --- Verification ---
        print("\n--- Clustering Stage Complete ---")
        print("Cluster distribution:")
        print(df_processed['cluster'].value_counts().sort_index())
        print("-" * 50)