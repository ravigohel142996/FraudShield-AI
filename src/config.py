"""
Configuration management for FraudShield AI
"""
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Data paths
DATA_DIR = PROJECT_ROOT / "data"
TRAINED_DIR = DATA_DIR / "trained"
SAMPLE_DATA_PATH = DATA_DIR / "sample_transactions.csv"

# Model paths
MODEL_PATH = TRAINED_DIR / "model.pkl"
SCALER_PATH = TRAINED_DIR / "scaler.pkl"

# Scoring weights
ML_WEIGHT = 0.6
RULES_WEIGHT = 0.4

# Risk thresholds
RISK_THRESHOLDS = {
    "low": 30,
    "medium": 60,
    "high": 100
}

# Feature definitions
REQUIRED_FEATURES = [
    'user_id',
    'amount',
    'timestamp',
    'merchant_category',
    'device_id',
    'ip_city',
    'bank_name',
    'account_age_days',
    'past_24h_txn_count',
    'past_7d_avg_amount',
    'is_night_txn',
    'is_new_device',
    'is_new_city'
]

# Model features (numeric only, excluding IDs)
MODEL_FEATURES = [
    'amount',
    'account_age_days',
    'past_24h_txn_count',
    'past_7d_avg_amount',
    'is_night_txn',
    'is_new_device',
    'is_new_city',
    'hour_of_day',
    'amount_to_avg_ratio'
]

# Merchant categories
MERCHANT_CATEGORIES = [
    'retail', 'grocery', 'electronics', 'travel',
    'entertainment', 'fuel', 'healthcare', 'restaurant',
    'utilities', 'education', 'gambling', 'crypto'
]

# Banks
BANKS = ['SBI', 'HDFC', 'ICICI', 'Axis', 'Kotak', 'Yes Bank', 'PNB', 'BOB']

# Cities
CITIES = [
    'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai',
    'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Surat'
]

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
TRAINED_DIR.mkdir(exist_ok=True)
