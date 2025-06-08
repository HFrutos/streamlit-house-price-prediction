#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Processing Script for Madrid Sale Properties

This script performs the following operations:
1.  Loads the raw property data scraped from pisos.com.
2.  Performs data cleaning and preprocessing, including:
    - Dropping irrelevant columns.
    - Renaming columns to a consistent, Pythonic format.
    - Handling missing values (NaNs).
    - Converting data types (e.g., object to float, object to boolean).
    - Parsing and transforming complex string columns into usable numerical or categorical features.
3.  Saves the cleaned, processed DataFrame to a new CSV file.

The script is designed to be a repeatable pipeline for preparing the raw data for
exploratory data analysis (EDA) and machine learning model training.
"""

# Standard library imports
import os
from pathlib import Path

# Third-party library imports
import pandas as pd
import numpy as np
import re

# --- Configuration Constants ---

# Define the project root directory assuming this script is in a 'scripts/' subdirectory
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Define paths for input (raw data) and output (processed data)
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
INPUT_FILENAME = "madrid_sale_properties_raw_1.csv" # Or your specific raw CSV file name
OUTPUT_FILENAME = "madrid_sale_properties_processed_1.csv"

INPUT_FILEPATH = RAW_DATA_DIR / INPUT_FILENAME
OUTPUT_FILEPATH = PROCESSED_DATA_DIR / OUTPUT_FILENAME

def load_data(filepath):
    """
    Loads data from a specified CSV file path into a pandas DataFrame.

    Args:
        filepath (Path object or str): The full path to the input CSV file.

    Returns:
        pandas.DataFrame or None: The loaded DataFrame, or None if the file is not found.
    """
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

# Load the dataset to begin processing
df_sale = load_data(INPUT_FILEPATH)

# --- Start of Data Processing Pipeline ---
# The following blocks will only run if the DataFrame was loaded successfully.
if df_sale is not None:
    # --- Drop Irrelevant Columns ---
    # These columns are identified as having very few non-null values or being
    # irrelevant for the initial modeling phase (e.g., internal references, redundant info).
    columns_to_drop = [
        'Agua', 'Calle alumbrada', 'Calle asfaltada', 'Carpintería exterior',
        'Carpintería interior', 'Comedor', 'Gas', 'Interior', 'Lavadero', 'Luz',
        'No se aceptan mascotas', 'page_source', 'Portero automático', 'Referencia',
        'scrape_status', 'Se aceptan mascotas', 'Soleado', 'Superficie solar',
        'Teléfono', 'Tipo de casa', 'Tipo suelo', 'Urbanizado'
    ]
    df_sale.drop(columns=columns_to_drop, inplace=True, errors='ignore')
    
    # --- Rename Columns ---
    # Column names are sanitized to be lowercase, use underscores instead of spaces,
    # and remove special characters.
    # Note: Accents are removed for simplicity (e.g., Baños -> banos).
    rename_mapping = {
        'property_native_id': 'property_id',
        'scraped_timestamp': 'scraped_at',
        'energy_certificate_main_classification': 'energy_cert_classification',
        'Adaptado a personas con movilidad reducida': 'adaptado_movilidad_reducida',
        'Aire acondicionado': 'aire_acondicionado',
        'Amueblado': 'amueblado',
        'Antigüedad': 'antiguedad',
        'Armarios empotrados': 'armarios_empotrados',
        'Ascensor': 'ascensor',
        'Balcón': 'balcon',
        'Baños': 'banos',
        'Calefacción': 'calefaccion',
        'Chimenea': 'chimenea',
        'Cocina equipada': 'cocina_equipada',
        'Conservación': 'conservacion',
        'Exterior': 'exterior',
        'Garaje': 'garaje',
        'Gastos de comunidad': 'gastos_comunidad',
        'Habitaciones': 'habitaciones',
        'Jardín': 'jardin',
        'Orientación': 'orientacion',
        'Piscina': 'piscina',
        'Planta': 'planta',
        'Puerta blindada': 'puerta_blindada',
        'Sistema de seguridad': 'sistema_seguridad',
        'Superficie construida': 'superficie_construida',
        'Superficie útil': 'superficie_util',
        'Terraza': 'terraza',
        'Trastero': 'trastero',
        'Vidrios dobles': 'vidrios_dobles'
    }
    df_sale.rename(columns=rename_mapping, inplace=True)

    # --- No Processing Columns ---
    # The following columns are deemed suitable for initial analysis without transformation
    # ['url', 'property_id', 'barrio', 'distrito', 'scraped_at', 'description',
    # 'energy_cert_classification', 'energy_consumption_rating', 'energy_emissions_rating',
    # 'antiguedad', 'banos', 'conservacion', 'habitaciones']

    # --- Handle Target Variable 'price_eur' ---
    # The target variable for our model is 'price'. Any rows where this value
    # is missing are not useful for training a supervised model, so they are dropped.
    df_sale.dropna(subset=['price_eur'], inplace=True)

    # --- Convert Latitude and Longitude to Float ---
    # Coordinates are parsed as objects with commas as decimal separators.
    # They need to be converted to a numeric type (float) for any geospatial analysis.
    for col in ['latitude', 'longitude']:
        if df_sale[col].dtype == 'object':
            df_sale[col] = pd.to_numeric(df_sale[col].str.replace(',', '.', regex=False), errors='coerce') 

    # --- Parse Energy Consumption and Emissions Values ---
    # Create new columns for the numerical values and drop the original text columns.
    df_sale['energy_consumption_kwh_m2_yr'] = pd.to_numeric(
        df_sale['energy_consumption_value'].str.extract(r'(\d+\.?\d*)', expand=False),
        errors='coerce'
    )
    df_sale['energy_emissions_kg_co2_m2_yr'] = pd.to_numeric(
        df_sale['energy_emissions_value'].str.extract(r'(\d+\.?\d*)', expand=False),
        errors='coerce'
    )
    df_sale.drop(columns=['energy_consumption_value', 'energy_emissions_value'], inplace=True, errors='ignore')

    # --- Convert Amenity Columns to Boolean ---
    # Many feature columns represent the presence or absence of an amenity (e.g., Elevator, Pool).
    # These columns have text or are NaN. They will be converted to a boolean type (True/False).
    # The logic is: if the original cell is not empty (not NaN), the amenity is present (True).
    # If it is empty (NaN), the amenity is absent (False).
    boolean_conversion_cols = [
        'adaptado_movilidad_reducida', 'aire_acondicionado', 'armarios_empotrados',
        'ascensor', 'balcon', 'calefaccion', 'chimenea', 'cocina_equipada',
        'exterior', 'garaje', 'jardin', 'piscina', 'puerta_blindada',
        'sistema_seguridad', 'terraza', 'trastero', 'vidrios_dobles'
    ]
    
    print("\n--- Converting amenity columns to boolean (True/False) ---")
    for col in boolean_conversion_cols:
        if col in df_sale.columns:
            initial_nulls = df_sale[col].isnull().sum()
            df_sale[col] = df_sale[col].notna()
            print(f"Column '{col}': Converted to boolean. Original NaNs ({initial_nulls}) are now False.")

    # --- Process 'amueblado' (Furnished) into Three Categories ---
    # This column requires special handling to create three states:
    # True: The property is furnished.
    # False: The property is explicitly not furnished (e.g., "No", "Vacío").
    # NaN: The furnished status is unknown.
    def map_furnished_status(value):
        if pd.isna(value):
            return np.nan # Keep NaN as NaN
        
        # Convert to lower string to handle case variations
        val_lower = str(value).lower()
        
        if val_lower in ['no', 'vacío', 'vacio']:
            return False
        else: # Any other non-null value implies some level of furnishing
            return True

    df_sale['amueblado'] = df_sale['amueblado'].apply(map_furnished_status).astype('boolean') # Use nullable boolean

    # --- Parse 'gastos_comunidad' ---
    # This is a very messy text field. For a first pass, we will extract the
    # first number we can find and assume it's the monthly fee. This is an
    # approximation and may require more advanced NLP for higher accuracy.
    # Approach: Extract the first sequence of digits, allowing for a single comma or dot as a decimal separator.
    df_sale['gastos_comunidad_eur'] = pd.to_numeric(
        df_sale['gastos_comunidad'].str.replace('.', '', regex=False).str.extract(r'(\d+[,.]?\d*)', expand=False).str.replace(',', '.', regex=False),
        errors='coerce'
    )
    df_sale.drop(columns=['gastos_comunidad'], inplace=True, errors='ignore')

    # --- Parse 'orientacion' (Orientation) ---
    # This is a multi-value categorical field. We will create separate boolean columns
    # for each of the four primary orientations (Norte, Sur, Este, Oeste).
    # A property can have multiple orientations.
    if 'orientacion' in df_sale.columns:
        orientacion_str = df_sale['orientacion'].str.lower().fillna('')
        df_sale['orientacion_norte'] = orientacion_str.str.contains('norte|n', na=False)
        df_sale['orientacion_sur'] = orientacion_str.str.contains('sur|su', na=False)
        df_sale['orientacion_este'] = orientacion_str.str.contains('este', na=False)
        df_sale['orientacion_oeste'] = orientacion_str.str.contains('oeste', na=False)
        df_sale.drop(columns=['orientacion'], inplace=True)

    # --- Parse 'planta' (Floor) ---
    # This ordinal categorical feature will be converted to a numerical scale.
    # Approach: Map text values like "Bajo" to 0, "Entresuelo" to 0.5,
    # and extract the number from strings like "1ª", "2ª", etc.
    def map_floor_number(value):
        if pd.isna(value):
            return np.nan
        val_lower = str(value).lower()
        if 'bajo' in val_lower: return 0
        if 'semisótano' in val_lower: return -1
        if 'entresuelo' in val_lower: return 0.5
        if 'principal' in val_lower: return 1.0 # Often the 1st floor
        if 'más de 20' in val_lower: return 21.0
        
        # Use regex to find numbers in strings like "1ª", "10ª", etc.
        numeric_part = re.search(r'(\d+)', val_lower)
        if numeric_part:
            return float(numeric_part.group(1))
        
        return np.nan # Return NaN if no mapping is found

    if 'planta' in df_sale.columns:
        df_sale['planta_numerica'] = df_sale['planta'].apply(map_floor_number)
        df_sale.drop(columns=['planta'], inplace=True)

    # --- Parse Surface Area Columns ---
    # Extract the numerical part and convert to a float type.
    for col in ['superficie_construida', 'superficie_util']:
        if col in df_sale.columns:
            df_sale[col] = pd.to_numeric(
                df_sale[col].astype(str).str.extract(r'(\d+\.?\d*)', expand=False),
                errors='coerce'
            )

    # --- Final Data Saving ---
    print("\n--- Final Step: Saving processed data ---")
    try:
        # Ensure the output directory exists
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        df_sale.to_csv(OUTPUT_FILEPATH, index=False, encoding='utf-8')
        print(f"Processed data successfully saved to: {OUTPUT_FILEPATH}")
    except Exception as e:
        print(f"An error occurred while saving the processed data: {e}")