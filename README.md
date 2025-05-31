# House Price Prediction App
A Streamlit web application that provides predictions for property sale and rental prices in Madrid, Spain. Data is collected via web scraping from pisos.com, and machine learning models are used for predictions.

## Table of Contents
- [House Price Prediction App](#house-price-prediction-app)
  - [Table of Contents](#table-of-contents)
  - [Project Overview](#project-overview)
  - [Features](#features)
  - [Technology Stack](#technology-stack)
  - [Project Structure](#project-structure)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Cloning](#cloning)
    - [Setup](#setup)
  - [Usage](#usage)
    - [1. Data Collection (Web Scraping)](#1-data-collection-web-scraping)
    - [2. Model Training (planned)](#2-model-training-planned)
    - [3. Running the Streamlit Application (planned)](#3-running-the-streamlit-application-planned)
- [Ensure your virtual environment is active](#ensure-your-virtual-environment-is-active)

## Project Overview
This project aims to build an end-to-end application for predicting house prices and rental rates in Madrid. It involves scraping data from pisos.com, processing the data, training machine learning models, and deploying an interactive frontend using Streamlit for users to get predictions and explore property data.

## Features
* Web scraping scripts to collect data for both sale and rental properties.
* Data cleaning and preprocessing pipeline.
* Machine learning model for price/rent prediction.
* Interactive Streamlit web application for:
    * Inputting property features to get a price/rent estimate.
    * Exploring visualizations of the property market data.

## Technology Stack
* **Python 3.12**
* **Web Scraping:** Requests, BeautifulSoup4
* **Data Manipulation:** Pandas, NumPy
* **Machine Learning:** Scikit-learn
* **Web Application:** Streamlit

## Project Structure
```bash
streamlit-house-price-prediction/
├── app/                       # Streamlit frontend
│   ├── main.py                # Core app (entry point to run the app)
│   ├── pages/                 # Sub-pages for the multi-page Streamlit app
│   │   ├── predict.py         # Prediction page
│   │   └── explore.py         # Data visualization page
│   ├── assets/                # Static assets like images, CSS files
│   └── utils/                 # Helper functions
│       ├── data_loader.py     # Load datasets
│       └── model_loader.py    # Load ML model
│── scrapers/                  # Scripts for web scraping property data
│   ├── scrape_pisos_rental.py # Script to scrape listings and details for SALE properties from pisos.com
│   └── scrape_pisos_sale.py   # Script to scrape listings and details for RENTAL properties from pisos.com
├── model/                     # Machine learning model-related files
│   ├── trained_model.pkl      # Serialized (saved) trained machine learning model
│   └── model_training.py      # Python script for training/retraining the ML model
├── data/                      # Datasets (only local, included in .gitignore)
│   ├── raw/                   # Original data (immutable)
│   └── processed/             # Cleaned/transformed data
├── notebooks/                 # Jupyter notebooks for experimentation and analysis
│   ├── EDA.ipynb              # Exploratory analysis
│   └── model_training.ipynb   # Model experiments
├── tests/                     # Automated tests for the project (e.g., unit, integration tests)
├── requirements.txt           # Dependencies
├── .gitignore                 # Specifies intentionally untracked files that Git should ignore
└── README.md                  # This file: project overview, setup, and usage instructions
```

## Getting Started

Follow these instructions to set up and run the project locally.

### Prerequisites
* Python 3.12 or later (not tested on 3.13)
* pip (Python package installer)
* Git

### Cloning
1.  Clone the repository to your local machine:
    ```bash
    git clone https://github.com/HFrutos/streamlit-house-price-prediction.git
    ```
2.  Navigate into the project directory:
    ```bash
    cd streamlit-house-price-prediction
    ```

### Setup
1.  **Create and activate a virtual environment:**
    It's highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    # Create a virtual environment (e.g., named 'venv')
    python3 -m venv venv
    
    # Activate it
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows (Git Bash):
    # source venv/Scripts/activate
    # On Windows (Command Prompt):
    # venv\Scripts\activate.bat
    ```
    You should see `(venv)` at the beginning of your terminal prompt.

2.  **Install dependencies:**
    Install all required Python packages from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Data Collection (Web Scraping)
The scripts to collect data from pisos.com are located in the `scrapers/` directory.
*Note: Web scraping should be done responsibly and in accordance with the website's terms of service and `robots.txt`.*

* **To scrape properties for sale:**
    ```bash
    # Ensure your virtual environment is active
    python scrapers/scrape_pisos_sale.py
    ```
    This will generate a CSV file in `data/raw/madrid_sale_properties_raw.csv`.

* **To scrape properties for rent:**
    ```bash
    # Ensure your virtual environment is active
    python scrapers/scrape_pisos_rental.py
    ```
    This will generate a CSV file in `data/raw/madrid_rental_properties_raw.csv`.

### 2. Model Training (planned)
Predicts house prices/rental rates based on property features.

Model training scripts and notebooks are available:
* Experimentation and development: `notebooks/model_training.ipynb` (planned)
* Script for retraining (if applicable): `model/model_training.py`(planned)
    ```bash
    # Example command if model_training.py is runnable
    python model/model_training.py
    ```
The trained model is saved as `model/trained_model.pkl`. (planned)

### 3. Running the Streamlit Application (planned)
To start the Streamlit web application:
```bash
# Ensure your virtual environment is active
streamlit run app/main.py