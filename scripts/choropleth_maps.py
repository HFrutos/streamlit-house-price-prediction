# generate_madrid_property_maps.py
#
# Python script for processing Madrid real estate data (rental and sale),
# merging it with geospatial neighborhood data, and generating interactive
# choropleth and point maps to visualize property counts, average prices,
# and individual property locations.

import os
import pandas as pd
import geopandas as gpd
import plotly.express as px
import requests # For downloading geospatial data

# --- Configuration Constants ---

# Input data files
# IMPORTANT: Update this paths if needed
RENTAL_CSV_PATH = '../data/raw/madrid_rental_properties_raw_1.csv'
SALE_CSV_PATH = '../data/raw/madrid_sale_properties_raw_1.csv'

# Geospatial data
GEOSPATIAL_DATA_URL = "https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/LIMITES_ADMINISTRATIVOS/Barrios/TopoJSON/Barrios.json"
GEODATA_DIR = '../data/geodata'
LOCAL_GEOJSON_FILENAME = "Barrios_Madrid_Oficial.json"
LOCAL_GEOJSON_PATH = os.path.join(GEODATA_DIR, LOCAL_GEOJSON_FILENAME)

# Output directory for maps
MAPS_OUTPUT_DIR = '../reports/maps'

# Column names from property CSV files (adjust if your column names differ)
# Common columns
NEIGHBORHOOD_COL = 'barrio'
LATITUDE_COL = 'latitude'
LONGITUDE_COL = 'longitude'

# Property type specific columns
RENTAL_PRICE_COL = 'rent_eur_per_month'
SALE_PRICE_COL = 'price_eur'

# Column names from GeoJSON (these are typical for Madrid's official GeoJSON)
GEOJSON_NEIGHBORHOOD_NAME_COL = 'NOMBRE'
GEOJSON_NEIGHBORHOOD_CODE_COL = 'COD_BAR'

# Map settings
MADRID_CENTER_LAT = 40.4168
MADRID_CENTER_LON = -3.7038
INITIAL_ZOOM = 10

# --- Helper Functions ---

def ensure_directory_exists(dir_path):
    """Checks if a directory exists, and creates it if it doesn't."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Created directory: {dir_path}")

def load_and_aggregate_property_data(csv_path, neighborhood_col, price_col, property_type_label):
    """
    Loads property data from a CSV, processes it, and aggregates it by neighborhood.

    Args:
        csv_path (str): Path to the input CSV file.
        neighborhood_col (str): Name of the neighborhood column in the CSV.
        price_col (str): Name of the price column in the CSV.
        property_type_label (str): Label for the property type (e.g., "Rental", "Sale") for messages.

    Returns:
        pandas.DataFrame: Aggregated data with property counts and average prices per neighborhood.
                          Returns None if loading or processing fails.
        pandas.DataFrame: Original loaded properties DataFrame with price column converted to numeric.
                          Returns None if loading or processing fails.
    """
    print(f"\n--- Processing {property_type_label} Properties from: {csv_path} ---")
    try:
        properties_df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: {property_type_label} properties file not found at {csv_path}")
        return None, None
    except Exception as e:
        print(f"Error loading {property_type_label} CSV {csv_path}: {e}")
        return None, None

    # Ensure the price column is numeric
    if price_col not in properties_df.columns:
        print(f"Error: Price column '{price_col}' not found in {property_type_label} DataFrame.")
        return None, None
    try:
        properties_df[price_col] = pd.to_numeric(properties_df[price_col], errors='coerce')
    except Exception as e:
        print(f"Error converting price column '{price_col}' to numeric for {property_type_label} data: {e}")
        return None, None

    # Drop rows where price could not be converted (became NaN)
    initial_rows = len(properties_df)
    properties_df.dropna(subset=[price_col], inplace=True)
    if len(properties_df) < initial_rows:
        print(f"Dropped {initial_rows - len(properties_df)} rows with invalid prices from {property_type_label} data.")

    if properties_df.empty:
        print(f"No valid {property_type_label} property data remaining after cleaning.")
        return pd.DataFrame(columns=[neighborhood_col, 'property_count', 'average_price']), properties_df # Return empty aggregated and original

    # 1. Calculate total property count per neighborhood
    property_counts = properties_df.groupby(neighborhood_col).size().reset_index(name='property_count')

    # 2. Calculate average price per neighborhood
    average_prices = properties_df.groupby(neighborhood_col)[price_col].mean().reset_index(name='average_price')

    # Merge the two aggregations
    aggregated_df = pd.merge(property_counts, average_prices, on=neighborhood_col, how='outer')

    print(f"Aggregated {property_type_label} property data per neighborhood (first 5 rows):")
    print(aggregated_df.head())
    return aggregated_df, properties_df


def get_madrid_geojson(url, local_path):
    """
    Downloads Madrid neighborhoods GeoJSON if not already present locally, then loads it.

    Args:
        url (str): URL to the geospatial data file.
        local_path (str): Local path to save/load the file.

    Returns:
        geopandas.GeoDataFrame: Loaded geospatial data. Returns None on failure.
    """
    ensure_directory_exists(os.path.dirname(local_path)) # Ensure geodata directory exists
    if os.path.exists(local_path):
        print(f"Loading local geospatial data from: {local_path}")
    else:
        print(f"Local geospatial data not found. Attempting to download from: {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Raise an exception for HTTP errors
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"Successfully downloaded geospatial data to {local_path}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading geospatial data: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during download: {e}")
            return None

    try:
        madrid_gdf = gpd.read_file(local_path)
        # Standardize CRS to EPSG:4326 if not already, common for web maps
        if madrid_gdf.crs is None:
            print("Warning: GeoJSON has no CRS defined. Assuming EPSG:4326 (WGS84).")
            madrid_gdf = madrid_gdf.set_crs("EPSG:4326", allow_override=True)
        elif str(madrid_gdf.crs).upper() != "EPSG:4326":
            print(f"Converting GeoJSON CRS from {madrid_gdf.crs.to_string()} to EPSG:4326.")
            madrid_gdf = madrid_gdf.to_crs("EPSG:4326")

        print("Geospatial data loaded successfully.")
        print(f"GeoDataFrame head:\n{madrid_gdf.head()}")
        return madrid_gdf
    except Exception as e:
        print(f"Error loading geospatial file {local_path}: {e}")
        return None


def correct_and_merge_data(aggregated_prop_df, geo_df, correction_map,
                           agg_neighborhood_col, geo_neighborhood_name_col):
    """
    Applies neighborhood name corrections to the aggregated property data
    and merges it with the geospatial DataFrame.

    Args:
        aggregated_prop_df (pd.DataFrame): Aggregated property data.
        geo_df (gpd.GeoDataFrame): Geospatial data of neighborhoods.
        correction_map (dict): Mapping from names in aggregated_prop_df to official names in geo_df.
        agg_neighborhood_col (str): Name of the neighborhood column in aggregated_prop_df.
        geo_neighborhood_name_col (str): Name of the neighborhood name column in geo_df.

    Returns:
        gpd.GeoDataFrame: Merged GeoDataFrame with property data and geometries.
    """
    if aggregated_prop_df is None or aggregated_prop_df.empty:
        print("Aggregated property data is empty or None. Skipping merge.")
        # Return the geo_df with empty columns for property data to allow map generation with no data
        geo_df['property_count'] = 0
        geo_df['average_price'] = pd.NA
        geo_df['barrio_corrected'] = geo_df[geo_neighborhood_name_col]
        return geo_df

    print("\n--- Correcting Neighborhood Names and Merging Data ---")
    # Create a 'barrio_corrected' column in aggregated_prop_df for merging
    aggregated_prop_df['barrio_corrected'] = aggregated_prop_df[agg_neighborhood_col].replace(correction_map)
    print("Applied initial correction map to aggregated property data.")

    # Perform a left merge to keep all neighborhoods from the GeoJSON
    merged_gdf = geo_df.merge(
        aggregated_prop_df,
        left_on=geo_neighborhood_name_col,
        right_on='barrio_corrected', # Merge on the corrected names
        how='left'
    )
    print("Merged property data with geospatial data.")

    # Post-merge specific corrections for 'barrio_corrected'
    # This ensures the 'barrio_corrected' column (which comes from property data side)
    # has the desired final display names for these specific cases.
    # The 'NOMBRE' column from geo_df remains the official geojson name.
    if 'barrio_corrected' in merged_gdf.columns: # Check if column exists (it should if merge happened)
        merged_gdf.loc[merged_gdf['barrio_corrected'] == 'Ángeles', 'barrio_corrected'] = 'Los Ángeles'
        merged_gdf.loc[merged_gdf['barrio_corrected'] == 'Águilas', 'barrio_corrected'] = 'Las Águilas'
        print("Applied final specific name corrections to 'barrio_corrected' column in merged data.")
    else: # This case occurs if aggregated_prop_df was empty and we constructed merged_gdf manually
        merged_gdf['barrio_corrected'] = merged_gdf[geo_neighborhood_name_col]


    # If 'barrio_corrected' is NaN for rows that only exist in geo_df (due to left merge),
    # fill it with the official neighborhood name from geo_df for display consistency.
    if 'barrio_corrected' in merged_gdf.columns:
        merged_gdf['barrio_corrected'] = merged_gdf['barrio_corrected'].fillna(merged_gdf[geo_neighborhood_name_col])

    # Handle missing data in merged DataFrame
    # Fill 'property_count' with 0 for neighborhoods with no property data
    merged_gdf['property_count'] = merged_gdf['property_count'].fillna(0)
    # 'average_price' is left as NaN (Plotly handles this by not coloring those regions)
    # Commented out alternative:
    # merged_gdf['average_price'] = merged_gdf['average_price'].fillna(0) # Or some other placeholder

    print("Final merged_gdf head (after corrections and NaN handling):")
    print(merged_gdf[[geo_neighborhood_name_col, 'barrio_corrected', 'property_count', 'average_price', 'geometry']].head())
    return merged_gdf


def create_choropleth_map(gdf, color_col, color_scale, title_text, labels_dict,
                          output_filename, neighborhood_display_col, custom_data_cols):
    """
    Generates and saves a choropleth map using Plotly Express.

    Args:
        gdf (gpd.GeoDataFrame): Merged GeoDataFrame containing data and geometries.
        color_col (str): Column name to use for coloring the choropleth.
        color_scale (str): Plotly color scale name.
        title_text (str): Title for the map.
        labels_dict (dict): Dictionary for customizing legend labels.
        output_filename (str): Full path to save the HTML map file.
        neighborhood_display_col (str): Column to use for hover name and potentially in tooltips.
        custom_data_cols (list): List of column names to include in custom_data for hover tooltips.
    """
    print(f"Generating choropleth map: {title_text}")
    if gdf is None or gdf.empty:
        print(f"Skipping map '{title_text}' as GeoDataFrame is empty or None.")
        return
    if color_col not in gdf.columns:
        print(f"Error: Color column '{color_col}' not found in GeoDataFrame. Skipping map '{title_text}'.")
        return

    # Check for invalid geometries. The map will still attempt to render but may have issues
    if 'geometry' in gdf.columns and not gdf.geometry.is_valid.all():
        print(f"Warning: Invalid geometries found in the GeoDataFrame for map '{title_text}'.")
        print("         The map will attempt to render, but some neighborhoods might have visual artifacts or be missing.")
        print("         This is often an issue with the source GeoJSON file.")

    # Validate that all columns for custom data exist in the GeoDataFrame
    valid_custom_data = [col for col in custom_data_cols if col in gdf.columns]
    missing_custom_data = [col for col in custom_data_cols if col not in gdf.columns]
    if missing_custom_data:
        print(f"Warning: Custom data columns not found and will be excluded from hover: {missing_custom_data}")

    fig = px.choropleth_map(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color=color_col,
        hover_name=neighborhood_display_col,
        custom_data=valid_custom_data,
        color_continuous_scale=color_scale,
        center={"lat": MADRID_CENTER_LAT, "lon": MADRID_CENTER_LON},
        zoom=INITIAL_ZOOM,
        opacity=0.7,
        labels=labels_dict,
        title=f"<b>{title_text}</b>"
    )

    fig.update_layout(margin={"r": 0, "t": 35, "l": 0, "b": 0})

    # Construct the hovertemplate string by explicitly referencing customdata fields.
    # This avoids ambiguity and issues where Plotly might not populate %{hover_name}
    # when a custom hovertemplate is in use.
    ht_parts = []
    
    # Part 1: Neighborhood Name (from custom_data)
    if neighborhood_display_col in valid_custom_data:
        name_idx = valid_custom_data.index(neighborhood_display_col)
        # The f-string uses double curly braces {{...}} to escape them for Python,
        # so Plotly receives the single curly braces it needs: %{customdata[index]}
        ht_parts.append(f"<b>%{{customdata[{name_idx}]}}</b><br>")
    else:
        # Fallback to hover_name if name column isn't in custom_data (should not happen)
        ht_parts.append("<b>%{hover_name}</b><br>")

    # Part 2: Property Count
    # Use '%{z}' if count is the main color, otherwise get it from customdata
    if color_col == 'property_count':
        ht_parts.append("Property Count: %{z}<br>")
    elif 'property_count' in valid_custom_data:
        count_idx = valid_custom_data.index('property_count')
        ht_parts.append(f"Property Count: %{{customdata[{count_idx}]}}<br>")

    # Part 3: Average Price
    # Use '%{z}' if price is the main color, otherwise get it from customdata
    if color_col == 'average_price':
        ht_parts.append("Average Price: %{z:,.0f} €<br>")
    elif 'average_price' in valid_custom_data:
        price_idx = valid_custom_data.index('average_price')
        ht_parts.append(f"Average Price: %{{customdata[{price_idx}]:,.0f}} €<br>")
    
    # Part 4: Extra tag to remove the secondary box
    ht_parts.append("<extra></extra>")
    
    hovertemplate = "".join(ht_parts)
    fig.update_traces(hovertemplate=hovertemplate)

    try:
        fig.write_html(output_filename)
        print(f"Map saved to: {output_filename}")
    except Exception as e:
        print(f"Error saving map {output_filename}: {e}")


def create_point_map(properties_df, price_col, lat_col, lon_col,
                     title_text, output_filename, property_type_label):
    """
    Generates and saves a scatter map (point map) of individual property locations.

    Args:
        properties_df (pd.DataFrame): DataFrame with individual property listings.
        price_col (str): Column name for property price (for hover).
        lat_col (str): Column name for latitude.
        lon_col (str): Column name for longitude.
        title_text (str): Title for the map.
        output_filename (str): Full path to save the HTML map file.
        property_type_label (str): "Rental" or "Sale" for hover info.
    """
    print(f"Generating point map: {title_text}")
    if properties_df is None or properties_df.empty:
        print(f"Skipping map '{title_text}' as properties DataFrame is empty or None.")
        return
    required_cols = [price_col, lat_col, lon_col]
    if not all(col in properties_df.columns for col in required_cols):
        print(f"Error: Missing one or more required columns for point map: {required_cols}. Skipping '{title_text}'.")
        return

    # Drop rows with missing lat/lon for plotting
    plot_df = properties_df.dropna(subset=[lat_col, lon_col, price_col]).copy()
    if plot_df.empty:
        print(f"No valid data points with lat/lon/price for map '{title_text}'.")
        return

    fig = px.scatter_map(
        plot_df,
        lat=lat_col,
        lon=lon_col,
        # color=price_col, # Optional: color points by price
        # color_continuous_scale="Viridis",
        color_discrete_sequence=["#3B0AAD"],
        size_max=10, # Adjust point size
        opacity=0.7,
        hover_name=NEIGHBORHOOD_COL, # Show neighborhood name if available
        custom_data=[price_col], # Price for hover
        center={"lat": MADRID_CENTER_LAT, "lon": MADRID_CENTER_LON},
        zoom=INITIAL_ZOOM,
        title=f"<b>{title_text}</b>",
        labels={price_col: f"{property_type_label} Price (€)"}
    )
    fig.update_layout(margin={"r": 0, "t": 35, "l": 0, "b": 0})
    fig.update_traces(
        hovertemplate=f"<b>{property_type_label} Property</b><br>" +
                      f"{property_type_label} Price: %{{customdata[0]:,.0f}} €<br>" +
                      # "Neighborhood: %{hovertext}<br>" + # If NEIGHBORHOOD_COL is hover_name
                      "<extra></extra>"
    )
    try:
        fig.write_html(output_filename)
        print(f"Map saved to: {output_filename}")
    except Exception as e:
        print(f"Error saving map {output_filename}: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Madrid Real Estate Map Generation Script...")
    ensure_directory_exists(MAPS_OUTPUT_DIR)
    ensure_directory_exists(GEODATA_DIR)


    # --- 1. Load Geospatial Data (common for all maps) ---
    madrid_geo_df = get_madrid_geojson(GEOSPATIAL_DATA_URL, LOCAL_GEOJSON_PATH)
    if madrid_geo_df is None:
        print("Critical error: Could not load geospatial data. Exiting.")
        exit()

    # --- 2. Define Neighborhood Name Correction Map ---
    # Key: name in property CSV, Value: official name in GeoJSON
    correction_map = {
        'Río Rosas': 'Ríos Rosas', 'Concepción': 'La Concepción', 'Cortes-Huertas': 'Cortes',
        'Cármenes': 'Los Cármenes', 'Embajadores-Lavapiés': 'Embajadores',
        'Ensanche de Vallecas-Valdecarros': 'Ensanche de Vallecas', 'Jerónimos': 'Los Jerónimos',
        'Justicia-Chueca': 'Justicia',
        'Las Águilas': 'Águilas',   # Will be corrected to 'Águilas' for merge, then 'Las Águilas' in 'barrio_corrected' post-merge
        'Los Ángeles': 'Ángeles',     # Will be corrected to 'Ángeles' for merge, then 'Los Ángeles' in 'barrio_corrected' post-merge
        'Mirasierra-Arroyo del Fresno': 'Mirasierra', 'Palos de Moguer': 'Palos de la Frontera',
        'Salvador': 'El Salvador', 'Universidad-Malasaña': 'Universidad',
        'Valdebebas-Valdefuentes': 'Valdefuentes'
        # Add other mappings as needed based on your data exploration
    }

    # --- 3. Process and Map RENTAL Properties ---
    print("\n" + "="*30 + " PROCESSING RENTAL DATA " + "="*30)
    agg_rental_df, rental_properties_df = load_and_aggregate_property_data(
        RENTAL_CSV_PATH, NEIGHBORHOOD_COL, RENTAL_PRICE_COL, "Rental"
    )

    if agg_rental_df is not None:
        merged_rental_gdf = correct_and_merge_data(
            agg_rental_df, madrid_geo_df.copy(), correction_map, # Use a copy of geo_df to avoid modification issues if reused
            NEIGHBORHOOD_COL, GEOJSON_NEIGHBORHOOD_NAME_COL
        )

        # Define the column used for display names on map (post-correction)
        neighborhood_display_col = 'barrio_corrected'

        # Choropleth Maps for Rental Data
        create_choropleth_map(
            merged_rental_gdf, 'property_count', "Blues",
            "Number of Rental Properties per Neighborhood (Madrid)",
            {'property_count': 'Number of Rentals'},
            os.path.join(MAPS_OUTPUT_DIR, 'madrid_property_count_map_rental.html'),
            neighborhood_display_col,
            custom_data_cols=['property_count', 'average_price', neighborhood_display_col]
        )
        create_choropleth_map(
            merged_rental_gdf, 'average_price', "YlOrRd",
            "Average Rental Price per Neighborhood (Madrid)",
            {'average_price': 'Average Rent (€/month)'},
            os.path.join(MAPS_OUTPUT_DIR, 'madrid_average_price_map_rental.html'),
            neighborhood_display_col,
            custom_data_cols=['property_count', 'average_price', neighborhood_display_col]
        )

        # Point Map for Rental Data
        if rental_properties_df is not None and not rental_properties_df.empty:
             create_point_map(
                rental_properties_df, RENTAL_PRICE_COL, LATITUDE_COL, LONGITUDE_COL,
                "Individual Rental Property Locations and Prices (Madrid)",
                os.path.join(MAPS_OUTPUT_DIR, 'madrid_individual_properties_map_rental.html'),
                "Rental"
            )
        else:
            print("Skipping rental point map due to no valid rental properties data.")

    else:
        print("Skipping map generation for rental properties due to data loading/aggregation issues.")


    # --- 4. Process and Map SALE Properties ---
    print("\n" + "="*30 + " PROCESSING SALE DATA " + "="*30)
    # Ensure you have a SALE_CSV_PATH defined and the file exists
    if not os.path.exists(SALE_CSV_PATH):
        print(f"Warning: Sale properties CSV not found at {SALE_CSV_PATH}. Skipping sale data processing.")
    else:
        agg_sale_df, sale_properties_df = load_and_aggregate_property_data(
            SALE_CSV_PATH, NEIGHBORHOOD_COL, SALE_PRICE_COL, "Sale"
        )

        if agg_sale_df is not None:
            merged_sale_gdf = correct_and_merge_data(
                agg_sale_df, madrid_geo_df.copy(), correction_map, # Use a copy
                NEIGHBORHOOD_COL, GEOJSON_NEIGHBORHOOD_NAME_COL
            )

            neighborhood_display_col = 'barrio_corrected' # Should be consistent

            # Choropleth Maps for Sale Data
            create_choropleth_map(
                merged_sale_gdf, 'property_count', "Blues", 
                "Number of Sale Properties per Neighborhood (Madrid)",
                {'property_count': 'Number of Properties for Sale'},
                os.path.join(MAPS_OUTPUT_DIR, 'madrid_property_count_map_sale.html'),
                neighborhood_display_col,
                custom_data_cols=['property_count', 'average_price', neighborhood_display_col]
            )
            create_choropleth_map(
                merged_sale_gdf, 'average_price', "YlOrRd", 
                "Average Sale Price per Neighborhood (Madrid)",
                {'average_price': 'Average Sale Price (€)'},
                os.path.join(MAPS_OUTPUT_DIR, 'madrid_average_price_map_sale.html'),
                neighborhood_display_col,
                custom_data_cols=['property_count', 'average_price', neighborhood_display_col]
            )

            # Point Map for Sale Data
            if sale_properties_df is not None and not sale_properties_df.empty:
                create_point_map(
                    sale_properties_df, SALE_PRICE_COL, LATITUDE_COL, LONGITUDE_COL,
                    "Individual Sale Property Locations and Prices (Madrid)",
                    os.path.join(MAPS_OUTPUT_DIR, 'madrid_individual_properties_map_sale.html'),
                    "Sale"
                )
            else:
                print("Skipping sale point map due to no valid sale properties data.")
        else:
            print("Skipping map generation for sale properties due to data loading/aggregation issues.")

    print("\nMap generation script finished.")