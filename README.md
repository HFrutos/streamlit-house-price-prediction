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
    - [2. Data Processing and Preparation](#2-data-processing-and-preparation)
    - [3. Generating Choropleth Maps](#3-generating-choropleth-maps)
    - [4. Model Training (planned)](#4-model-training-planned)
    - [5. Running the Streamlit Application](#5-running-the-streamlit-application)
  - [File Attributes (`.gitattributes`)](#file-attributes-gitattributes)
  - [License](#license)

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
├── app/                       # Streamlit frontend application
│   ├── main.py                # Core app (entry point: streamlit run app/main.py)
│   ├── pages/                 # Sub-pages for the multi-page Streamlit app
│   │   ├── predict.py         # Prediction page
│   │   └── explore.py         # Data visualization page
│   ├── assets/                # Static assets (images, custom CSS)
│   └── utils/                 # Utility functions shared across the Streamlit app
│       ├── data_loader.py     # Load datasets
│       └── model_loader.py    # Load ML model
│
├── data/                      # Datasets (only local, included in .gitignore)
│   ├── raw/                   # Original data (immutable)
│   ├── processed/             # Cleaned/transformed/aggregated data
│   └── geodata/               # Geospatial data
│
├── notebooks/                 # Jupyter notebooks for experimentation, analysis, and research
│   ├── EDA.ipynb              # Exploratory analysis
│   └── model_training.ipynb   # Model experiments
│
├── model/                     # Machine learning model-related files
│   ├── trained_model.pkl      # Serialized (saved) trained machine learning model
│   └── model_training.py      # Python script for training/retraining the ML model
│
├── reports/                   # Generated reports, visualizations, and static outputs
│   ├── figures/               # Static plots or charts (e.g., PNG, SVG from EDA)
│   └── maps/                  # Generated interactive map HTML files
│
├── scrapers/                  # Scripts for web scraping property data
│   ├── scrape_pisos_rental.py # Scrapes rental properties
│   └── scrape_pisos_sale.py   # Scrapes sale properties
│
├── scripts/                   # Standalone utility or processing scripts
│   ├── choropleth_maps.py     # Script for creating map HTML files
│   ├── process_sale_data.py   # Script for cleaning and transforming raw sale data
│   └── process_rental_data.py   # Script for cleaning and transforming raw rental data
│
├── sql/                       # SQL scripts for database schema, staging, ETL, queries, etc.
│   ├── 01_schema.sql
│   ├── 02_staging.sql
│   ├── 03_etl.sql
│   └── README.md              # (Optional) Explanation of the SQL scripts and database setup
│
├── tests/                     # Automated tests for the project (e.g., unit, integration tests)
│   ├── unit/                  # Unit tests for individual functions/modules
│   └── integration/           # Integration tests for combined parts of the system
│
├── .env.example               # Template for environment variables (secrets should be in a local .env file)
├── .gitattributes             # Defines attributes for paths/files for Git
├── .gitignore                 # Specifies intentionally untracked files
├── LICENSE.md                 # Project license information
├── requirements.txt           # Dependencies
└── README.md                  # This file: Project overview, setup, and usage instructions
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

Follow these steps to get your local development environment configured for the project.

1.  **Create and activate a virtual environment:**
    It's highly recommended to use a virtual environment to manage project dependencies and isolate your project from other Python installations.
    ```bash
    # Create a virtual environment (e.g., named 'venv') in your project root
    python3 -m venv venv
    
    # Activate it
    # On macOS/Linux:
    source venv/bin/activate
    # On Windows (Git Bash):
    # source venv/Scripts/activate
    # On Windows (Command Prompt):
    # venv\Scripts\activate.bat
    ```
    After activation, you should see `(venv)` (or your chosen environment name) at the beginning of your terminal prompt.

2.  **Install dependencies:**
    Once your virtual environment is active, install all required Python packages listed in `requirements.txt`:
    ```bash
    # Ensure you are in the project root directory where requirements.txt is located
    pip install -r requirements.txt
    ```

3.  **Set up Environment Variables (`.env`):**
    This project uses a `.env` file to manage environment-specific configurations and sensitive information, such as database credentials or API keys. This practice ensures that secrets are not hardcoded into the source code and are not committed to the version control system.

    * **Key Files involved:**
        * **`.env` (Local and Ignored):**
            * This file should be created by you in the root directory of the project.
            * It will contain the actual secret values for your **local development environment**.
            * **IMPORTANT:** The `.env` file is listed in `.gitignore` and **MUST NEVER be committed** to the GitHub repository.
        * **`.env.example` (Version Controlled Template):**
            * This file **IS committed** to the repository and serves as a template.
            * It shows all the necessary environment variables that the project requires, typically with placeholder or empty values.

    * **Setup Instructions for your local `.env` file:**
        1.  **Locate `.env.example`**: In the project root, you'll find the file named `.env.example`.
        2.  **Create your local `.env` file**: Make a copy of `.env.example` and name it `.env`. You can do this in your terminal from the project root:
            ```bash
            cp .env.example .env
            ```
        3.  **Edit `.env`**: Open your newly created `.env` file with a text editor. Replace the placeholder values with your actual local credentials and any other required configuration values. For example:
            ```env
            # Example content for .env (replace with your actual values)
            DB_HOST="your_local_db_host"
            DB_PORT="3306"
            DB_NAME="your_local_db_name"
            DB_USER="your_local_db_user"
            DB_PASSWORD="your_secret_password"
            # ANY_OTHER_API_KEY="your_api_key_value"
            ```

    * **Usage in the Project:**
        * The Python scripts in this project (including the Streamlit app and scrapers, if they need such configurations) use the `python-dotenv` library to load the variables from your local `.env` file into the script's runtime environment.
        * Make sure `python-dotenv` is listed in your `requirements.txt` file (it should have been installed in step 2).

    This local `.env` setup allows each collaborator to maintain their own secrets without exposing them in the shared codebase. For production or deployed environments, similar environment variables would typically be configured directly on the server or cloud platform.

## Usage

This section outlines how to use the different components of the project, from data collection to running the application. Ensure your virtual environment is active (`source venv/bin/activate`) before running any Python scripts.

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

### 2. Data Processing and Preparation
Once raw data is collected, you may need to process and clean it. Scripts for these tasks can be found in the `scripts/` directory.

* **Example: Process raw sale data (if you have `scripts/process_sale_data.py`):**
    ```bash
    python scripts/process_sale_data.py
    ```
    This would typically take data from `data/raw/` and output cleaned data to `data/processed/`.

### 3. Generating Choropleth Maps
To visualize property data (e.g., number of properties per neighborhood, average prices) on interactive choropleth maps:

* **Run the map generation script:**
    ```bash
    python scripts/generate_choropleth_maps.py
    ```
    This script uses processed data and geospatial information (e.g., from `data/geodata/`) to create interactive HTML maps.
* **Output:** The generated maps will be saved in the `reports/maps/` directory (e.g., `madrid_property_counts_map.html`, `madrid_average_price_map.html`). You can open these HTML files directly in a web browser to view the maps.

### 4. Model Training (planned)
This project aims to predict house prices and rental rates based on property features.

* **Experimentation & Development:** Jupyter Notebooks for model development and initial experiments can be found in `notebooks/` (e.g., `notebooks/model_training_experiments.ipynb`).
* **Training Script:** A more finalized script for training or retraining the model is located at `model/model_training.py`.
    ```bash
    # Example command to run the model training script
    python model/model_training.py
    ```
    The trained model is typically saved to a file like `model/trained_model.pkl`.

### 5. Running the Streamlit Application
The interactive web application allows users to get price predictions and explore property data visualizations.

* **To start the Streamlit web application:**
    ```bash
    # Ensure you are in the project root directory
    streamlit run app/main.py
    ```
    This will typically open the application in your default web browser. The app might use the trained model (`model/trained_model.pkl`) and processed datasets. The `explore.py` page within the app could also be a place to display the generated choropleth maps or similar visualizations dynamically.

## File Attributes (`.gitattributes`)

This project includes a `.gitattributes` file to manage how Git handles line endings and identifies file types. This helps ensure consistency across different operating systems and development environments.

Key configurations include:

* **Default Normalization:** All files are automatically assessed, and text files are normalized to use LF (Unix-style) line endings in the repository.
* **Specific Text Files:** Files like `*.py`, `*.md`, `*.json`, `*.txt`, etc., are explicitly treated as text and normalized to LF.
* **Binary Files:** Files like `*.png`, `*.jpg`, `*.pkl`, etc., are explicitly treated as binary to prevent corruption by line-ending conversions or improper diffing.

Collaborators generally do not need to take any specific action regarding this file; Git will use its rules automatically when you commit and check out files. This setup promotes a cleaner version history and easier collaboration.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
