# app/main.py

import streamlit as st

# --- Page Configuration ---
st.set_page_config(
    page_title="Madrid Property Price Predictor",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Main Content ---

# Title of the app
st.title("Madrid Property Price Prediction App 🏠")

# Introduction using Markdown
st.markdown("""
Welcome to the Madrid Property Price Prediction application!

This tool is designed to provide insights into the dynamic real estate market of Madrid, covering both properties for sale and for rent.

**What you can do:**
- 🗺️ **Explore Data:** Navigate to the "Explore Sale Data" or "Explore Rental Data" pages to view interactive maps and visualizations.
- 📈 **Get Predictions:** Use the "Predict Price" page to estimate the value of a property based on its features (coming soon!).
- 📊 **Compare Properties:** Use the "Compare Properties" page to see a side-by-side comparison of two properties based on their most important features.

Use the sidebar on the left to navigate between the different sections of the application.
""")

# --- Sidebar Content ---
st.sidebar.success("Select a page above to get started.")

st.sidebar.markdown("""
---
Created by streamlit-house-price-prediction Contributors.
""")