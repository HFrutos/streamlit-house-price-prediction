#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Feature Importance and Radar Plot Comparison for Madrid Sale Properties

This script performs the following steps:
1.  Loads the cleaned 'for sale' property dataset.
2.  Prepares the data for machine learning by dropping irrelevant columns and
    transforming categorical features (including high-cardinality location features
    like 'barrio' and 'distrito' using Target Encoding).
3.  Handles missing values using median imputation.
4.  Scales all features to a common range (0-1) for visualization.
5.  Trains a RandomForestRegressor model to determine feature importance.
6.  Defines a function to generate an interactive radar plot comparing two properties
    based on the most important features.
"""

# Standard library imports
from pathlib import Path

# Third-party library imports
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
import plotly.graph_objects as go

# --- Configuration Constants ---

# Define project paths assuming this script is in a 'scripts/' subdirectory
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures" 

# Define input file
INPUT_FILENAME = "madrid_sale_properties_processed_1.csv"
INPUT_FILEPATH = PROCESSED_DATA_DIR / INPUT_FILENAME


# --- Load the Cleaned Dataset ---

def load_data(filepath):
    """Loads the processed dataset from a CSV file."""
    print(f"Attempting to load data from: {filepath}")
    if not filepath.exists():
        print(f"Error: Input file not found at {filepath}")
        return None
    try:
        df = pd.read_csv(filepath)
        print("Data loaded successfully.")
        print(f"Initial dataset shape: {df.shape}")
        return df
    except Exception as e:
        print(f"An error occurred while loading the data: {e}")
        return None

df_sale = load_data(INPUT_FILEPATH)


# --- Drop Unnecessary Columns for Modeling ---

# These columns are either identifiers, redundant, un-featurized, or not useful for the model.
columns_to_drop = [
    'url', 'property_id',
    'scraped_at',
    'energy_cert_classification', # Text-based, ratings are used instead
    'description',
    'superficie_util', # Highly correlated with superficie_construida, and has more NaNs
    'orientacion_list'
]

if df_sale is not None:
    df_sale.drop(columns=columns_to_drop, inplace=True, errors='ignore')


# --- Preprocessing and Feature Engineering ---
if df_sale is not None:
    print("\n--- Preprocessing data for modeling ---")
    
    # Keep a copy of the original location names for later use in plotting
    original_locations = df_sale[['barrio', 'distrito']].copy()
    
    # --- Target Encoding for 'barrio' and 'distrito' ---
    # Target encoding is a powerful technique for high-cardinality categorical features.
    # We replace each category (e.g., a neighborhood name) with the mean of the
    # target variable (price_eur) for that category.
    # Note: For formal model training, this should be done carefully within a cross-validation
    # loop to prevent data leakage. For this feature importance analysis, applying it
    # to the whole dataset is a reasonable simplification.
    
    # First, handle any missing location data by filling with a placeholder.
    df_sale['barrio'] = df_sale['barrio'].fillna('Desconocido')
    df_sale['distrito'] = df_sale['distrito'].fillna('Desconocido')
    
    # Calculate the mean price for each barrio and distrito
    barrio_price_map = df_sale.groupby('barrio')['price_eur'].mean()
    distrito_price_map = df_sale.groupby('distrito')['price_eur'].mean()
    
    # Create new encoded columns by mapping the means back to the original columns
    df_sale['barrio_encoded'] = df_sale['barrio'].map(barrio_price_map)
    df_sale['distrito_encoded'] = df_sale['distrito'].map(distrito_price_map)
    
    # Drop the original object-type location columns
    df_sale.drop(columns=['barrio', 'distrito'], inplace=True)
    print("Applied Target Encoding to 'barrio' and 'distrito'.")

    # Ordinal Encoding for Energy Ratings
    energy_rating_map = {'G': 0, 'F': 1, 'E': 2, 'D': 3, 'C': 4, 'B': 5, 'A': 6}
    df_sale['energy_consumption_rating'] = df_sale['energy_consumption_rating'].map(energy_rating_map)
    df_sale['energy_emissions_rating'] = df_sale['energy_emissions_rating'].map(energy_rating_map)
    print("Encoded energy ratings.")

    # Ordinal Encoding for 'antiguedad' (Age)
    age_map = {
        'Más de 50 años': 0, 'Entre 30 y 50 años': 1, 'Entre 20 y 30 años': 2,
        'Entre 10 y 20 años': 3, 'Entre 5 y 10 años': 4, 'Menos de 5 años': 5
    }
    df_sale['antiguedad'] = df_sale['antiguedad'].map(age_map)
    print("Encoded 'antiguedad'.")

    # Ordinal Encoding for 'conservacion' (Condition)
    condition_map = {'A reformar': 0, 'En buen estado': 1, 'Reformado': 2, 'A estrenar': 3}
    df_sale['conservacion'] = df_sale['conservacion'].map(condition_map)
    print("Encoded 'conservacion'.")

    # One-Hot Encoding for 'amueblado' (Furnished)
    df_sale = pd.get_dummies(df_sale, columns=['amueblado'], prefix='amueblado', dummy_na=True)
    print("One-hot encoded 'amueblado'.")

    # Imputing Missing Values with Median
    for col in df_sale.select_dtypes(include=np.number).columns:
        if df_sale[col].isnull().any():
            median_val = df_sale[col].median()
            df_sale[col] = df_sale[col].fillna(median_val)
            print(f"Imputed NaNs in numerical column '{col}' with median value: {median_val:.2f}")


# --- Scale Data and Determine Feature Importance ---
if df_sale is not None:
    print("\n--- Scaling data and finding feature importances ---")
    
    # Define features (X) and target (y)
    X = df_sale.drop(columns=['price_eur'])
    y = df_sale['price_eur']

    # Scale all features to a range of [0, 1].
    scaler = MinMaxScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns, index=X.index)
    print("All features scaled using MinMaxScaler.")

    # Train a RandomForestRegressor to get feature importances
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_scaled, y)
    print("RandomForestRegressor model trained.")

    # Create a DataFrame of feature importances
    feature_importances = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False).reset_index(drop=True)

    # --- Verification ---
    print("\nTop 10 most important features:")
    print(feature_importances.head(10))
    print("-" * 50)


# --- Create and Display Radar Plot ---
if df_sale is not None:
    print("\n--- Defining radar plot function and generating visualization ---")

    def create_comparison_radar(df_scaled, df_unscaled, original_locations, importances_df, property_index_1, property_index_2, num_features=8):
        """
        Creates an interactive radar plot to compare two properties based on the most important features.
        
        This revised version:
        - Displays original, unscaled values with context-appropriate formatting on hover
        (e.g., integers for rooms, full precision for coordinates).
        - Ensures the radar plot polygon is properly closed.
        - Adjusts axis range to prevent hover labels from being obscured.

        Args:
            df_scaled (pd.DataFrame): DataFrame with scaled feature data.
            df_unscaled (pd.DataFrame): DataFrame with original, unscaled feature data.
            original_locations (pd.DataFrame): DataFrame with original barrio and distrito names.
            importances_df (pd.DataFrame): DataFrame of feature importances.
            property_index_1 (int): The DataFrame index of the first property.
            property_index_2 (int): The DataFrame index of the second property.
            num_features (int, optional): Number of top features to display. Defaults to 8.

        Returns:
            plotly.graph_objects.Figure: The generated radar plot figure.
        """
        # Select the top N most important features
        top_features = importances_df['feature'].head(num_features).tolist()

        # --- Data Preparation for Plotting ---
        
        # Get the scaled data for the plot's geometry
        prop1_scaled_r = df_scaled.loc[property_index_1, top_features].tolist()
        prop2_scaled_r = df_scaled.loc[property_index_2, top_features].tolist()
        
        # --- Create the custom hover text with original values and intelligent formatting ---
        hover_text_1, hover_text_2 = [], []
        for feat in top_features:
            # For encoded features, get the original name from the 'original_locations' DataFrame
            if feat == 'barrio_encoded':
                hover_text_1.append(f"barrio: {original_locations.loc[property_index_1, 'barrio']}")
                hover_text_2.append(f"barrio: {original_locations.loc[property_index_2, 'barrio']}")
            elif feat == 'distrito_encoded':
                hover_text_1.append(f"distrito: {original_locations.loc[property_index_1, 'distrito']}")
                hover_text_2.append(f"distrito: {original_locations.loc[property_index_2, 'distrito']}")
            
            # For latitude and longitude, show full precision
            elif feat in ['latitude', 'longitude']:
                val1 = df_unscaled.loc[property_index_1, feat]
                val2 = df_unscaled.loc[property_index_2, feat]
                hover_text_1.append(f'{feat}: {val1}') # Default string conversion preserves all decimals
                hover_text_2.append(f'{feat}: {val2}')
                
            # For all other numeric features, apply conditional formatting
            else:
                val1 = df_unscaled.loc[property_index_1, feat]
                val2 = df_unscaled.loc[property_index_2, feat]
                
                # Check if the value is a whole number (e.g., 2.0) and format as integer if so
                format1 = f'{int(val1)}' if pd.notna(val1) and val1 == int(val1) else f'{val1:,.2f}'
                format2 = f'{int(val2)}' if pd.notna(val2) and val2 == int(val2) else f'{val2:,.2f}'
                
                hover_text_1.append(f'{feat}: {format1}')
                hover_text_2.append(f'{feat}: {format2}')

        # To close the radar plot, append the first item to the end of each list
        closed_theta = top_features + [top_features[0]]
        closed_r1 = prop1_scaled_r + [prop1_scaled_r[0]]
        closed_r2 = prop2_scaled_r + [prop2_scaled_r[0]]
        closed_hover1 = hover_text_1 + [hover_text_1[0]]
        closed_hover2 = hover_text_2 + [hover_text_2[0]]

        # --- Create the Figure ---
        fig = go.Figure()

        # Add trace for Property 1
        fig.add_trace(go.Scatterpolar(
            r=closed_r1,
            theta=closed_theta,
            fill='toself',
            name=f'Property Index {property_index_1}',
            hovertext=closed_hover1,
            hoverinfo='text' 
        ))

        # Add trace for Property 2
        fig.add_trace(go.Scatterpolar(
            r=closed_r2,
            theta=closed_theta,
            fill='toself',
            name=f'Property Index {property_index_2}',
            hovertext=closed_hover2,
            hoverinfo='text'
        ))

        # Update layout
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1.05] 
                )),
            showlegend=True,
            title=f'Comparison of Properties {property_index_1} vs. {property_index_2}<br><i>(Hover for original values)</i>',
            template='plotly_dark'
        )
        
        return fig

    # --- Example Usage and Verification ---
    prop_idx_1 = 5
    prop_idx_2 = 10
    
    print(f"Generating comparison radar plot for properties with index {prop_idx_1} and {prop_idx_2}...")
    
    # Generate the plot, passing the new 'original_locations' DataFrame
    radar_fig = create_comparison_radar(
        df_scaled=X_scaled,
        df_unscaled=X,
        original_locations=original_locations, # Pass the new DataFrame here
        importances_df=feature_importances,
        property_index_1=prop_idx_1,
        property_index_2=prop_idx_2,
        num_features=8
    )

    
    # Ensure the output directory for figures exists.
    # parents=True creates parent directories (e.g., 'reports') if they don't exist.
    # exist_ok=True prevents an error if the directory already exists.
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Define a dynamic and descriptive filename for the plot.
    plot_filename = f"radar_comparison_sale_prop_{prop_idx_1}_vs_{prop_idx_2}.html"
    output_plot_path = FIGURES_DIR / plot_filename

    # Save the plot as an interactive HTML file.
    try:
        radar_fig.write_html(output_plot_path)
        print(f"Radar plot successfully saved to: {output_plot_path}")
    except Exception as e:
        print(f"An error occurred while saving the plot: {e}")

    # (Optional) You can comment out the line below or keep it if you still
    # want the plot to open in a browser automatically when you run the script.
    # radar_fig.show()

    print("\n--- Script finished ---")

else:
    print("\n--- Script did not run due to data loading failure ---")

    print("\n--- Script finished ---")