# House Price Prediction App
*Streamlit frontend for Madrid property price prediction.*

## Quick Start
1. Clone the repo.
2. Set up Python 3.12 and `requirements.txt`.

## Project Structure (draft)
```bash
streamlit-house-price-prediction/
├── app/                      # Streamlit frontend
│   ├── main.py               # Core app (runs Streamlit)
│   ├── pages/                # Multi-page app support (optional)
│   │   ├── predict.py        # Prediction page
│   │   └── explore.py       # Data visualization page
│   ├── assets/               # Images, CSS, configs
│   └── utils/                # Helper functions
│       ├── data_loader.py    # Load datasets
│       └── model_loader.py   # Load ML model
├── model/                    # Serialized models
│   ├── trained_model.pkl     # (e.g., scikit-learn)
│   └── model_training.py     # Script to retrain model
├── data/                     # Datasets
│   ├── raw/                  # Original data (immutable)
│   └── processed/            # Cleaned/transformed data
├── notebooks/                # Jupyter notebooks
│   ├── EDA.ipynb             # Exploratory analysis
│   └── model_training.ipynb  # Model experiments
├── tests/                    # Unit/integration tests
├── requirements.txt          # Dependencies
├── .gitignore                # Ignore data/model files
└── README.md                 # Setup + demo
```
