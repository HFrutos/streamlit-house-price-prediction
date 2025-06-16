# app/pages/1_Explore_Sale_Data.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
import json
import streamlit.components.v1 as components

# --- Page Configuration ---
st.set_page_config(
    page_title="Explore Sale Data",
    page_icon="📈",
    layout="wide"
)

# --- Data Loading with Caching ---
# Streamlit's cache decorator helps prevent reloading data on every interaction,
# which makes the app much faster.
@st.cache_data
def load_data(filepath):
    """Loads the processed sales dataset."""
    if not filepath.exists():
        st.error(f"Data file not found: {filepath}")
        return None
    df = pd.read_csv(filepath)
    return df

# --- Outlier Detection Functions ---

def find_outliers_tukey(df, column):
    """Finds outliers using the Tukey's Fence (IQR) method."""
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    return outliers

def find_outliers_zscore(df, column, threshold=3):
    """Finds outliers using the Z-score method."""
    mean = df[column].mean()
    std = df[column].std()
    z_scores = (df[column] - mean) / std
    outliers = df[np.abs(z_scores) > threshold]
    return outliers

# DBSCAN requires scikit-learn
try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler

    def find_outliers_dbscan(df, column, eps=0.5, min_samples=5):
        """Finds outliers using DBSCAN."""
        # DBSCAN works on a 2D array, so we reshape the column
        data = df[[column]].dropna()
        # Scale data for DBSCAN, as it's distance-based
        data_scaled = StandardScaler().fit_transform(data)
        
        db = DBSCAN(eps=eps, min_samples=min_samples).fit(data_scaled)
        # Outliers in DBSCAN are assigned the label -1
        outlier_indices = data[db.labels_ == -1].index
        return df.loc[outlier_indices]

except ImportError:
    # If scikit-learn is not installed, we can't use DBSCAN.
    def find_outliers_dbscan(df, column, eps=0.5, min_samples=5):
        st.error("Scikit-learn is required for DBSCAN. Please install it.")
        return pd.DataFrame()


# --- Page Content ---
st.title("📈 Explore Madrid Sale Properties")

# Define path to the processed data file
SCRIPT_DIR = Path(__file__).resolve().parent.parent # -> app/
PROJECT_ROOT = SCRIPT_DIR.parent # -> project root
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
INPUT_FILENAME = "madrid_sale_properties_processed_1.csv" # Use your actual processed file name
FILE_PATH = PROCESSED_DATA_DIR / INPUT_FILENAME

# Load the data
df_sale = load_data(FILE_PATH)

if df_sale is not None:
    
    # --- Section 1: Outlier Analysis ---
    st.header("Outlier Detection in Key Features")
    st.markdown("Use the selectors below to choose a feature and a detection method to identify outliers.")

    # Create two columns for selectors
    col1, col2 = st.columns(2)

    with col1:
        # Selector for the column to analyze
        feature_to_analyze = st.selectbox(
            "Select a feature for outlier analysis:",
            options=['price_eur', 'superficie_construida', 'habitaciones', 'banos'],
            index=0 # Default to price_eur
        )

    with col2:
        # Selector for the outlier detection method
        outlier_method = st.selectbox(
            "Select an outlier detection method:",
            options=["Tukey's Fence (IQR)", "Z-Score", "DBSCAN"],
            index=0
        )

    # Find outliers based on user selection
    if outlier_method == "Tukey's Fence (IQR)":
        outliers_df = find_outliers_tukey(df_sale, feature_to_analyze)
    elif outlier_method == "Z-Score":
        outliers_df = find_outliers_zscore(df_sale, feature_to_analyze)
    else: # DBSCAN
        # Add sliders for DBSCAN parameters for interactivity
        st.sidebar.header("DBSCAN Parameters")
        eps_val = st.sidebar.slider("EPS (neighborhood distance)", 0.1, 2.0, 0.5, 0.1)
        min_samples_val = st.sidebar.slider("Min Samples", 3, 20, 5, 1)
        outliers_df = find_outliers_dbscan(df_sale, feature_to_analyze, eps=eps_val, min_samples=min_samples_val)

    # Display the histogram
    st.subheader(f"Histogram of '{feature_to_analyze}' with Detected Outliers")
    fig_hist = px.histogram(
        df_sale,
        x=feature_to_analyze,
        title=f"Distribution of {feature_to_analyze}"
    )
    # Add a vertical line/shape for each outlier
    if not outliers_df.empty:
        for outlier_val in outliers_df[feature_to_analyze]:
            fig_hist.add_vline(x=outlier_val, line_dash="dash", line_color="red", annotation_text="outlier")
    st.plotly_chart(fig_hist, use_container_width=True)

    # Display the table of outliers
    st.subheader("Detected Outlier Properties")
    st.write(f"Found {len(outliers_df)} outliers using the **{outlier_method}** method for **{feature_to_analyze}**.")
    st.dataframe(outliers_df)

    st.divider() # Visual separator

    # --- Section 2: Price vs. Surface Area Scatter Plot ---
    st.header("Price vs. Built Area by Neighborhood")
    st.markdown("This scatter plot shows the relationship between property price and its size, segmented by neighborhood (`barrio`).")
    
    # Generate scatter plot
    fig_scatter = px.scatter(
        df_sale.dropna(subset=['price_eur', 'superficie_construida', 'barrio']), # Drop NaNs for plotting
        x="superficie_construida",
        y="price_eur",
        color="barrio", # Segment data by neighborhood
        hover_name="barrio",
        hover_data={'price_eur': ':,', 'superficie_construida': ':.2f'}, # Format hover data
        title="Price vs. Built Area"
    )
    fig_scatter.update_layout(xaxis_title="Built Area (m²)", yaxis_title="Price (€)")
    st.plotly_chart(fig_scatter, use_container_width=True)

else:
    st.warning("Could not load data. Please ensure the processed data file exists at the correct path.")