"""
Data storage and persistence utilities
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

from src.config import SAMPLE_DATA_PATH, MERCHANT_CATEGORIES, BANKS, CITIES


def generate_synthetic_data(n_samples=10000):
    """
    Generate synthetic transaction data with realistic fraud patterns
    
    Args:
        n_samples: Number of transactions to generate
        
    Returns:
        DataFrame with synthetic transactions
    """
    np.random.seed(42)
    random.seed(42)
    
    data = []
    
    # Generate base date
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(n_samples):
        # Random timestamp within last 30 days
        days_offset = random.randint(0, 29)
        hours_offset = random.randint(0, 23)
        timestamp = base_date + timedelta(days=days_offset, hours=hours_offset)
        
        # Determine if this should be fraud (10% fraud rate)
        is_fraud = random.random() < 0.10
        
        # Generate features with fraud correlation
        if is_fraud:
            # Fraud transactions have specific patterns
            amount = random.uniform(5000, 50000)  # Higher amounts
            account_age_days = random.randint(0, 30)  # Newer accounts
            past_24h_txn_count = random.randint(5, 20)  # More transactions
            past_7d_avg_amount = random.uniform(500, 2000)
            is_night_txn = random.random() < 0.6  # More likely at night
            is_new_device = random.random() < 0.7  # More likely new device
            is_new_city = random.random() < 0.6  # More likely new city
            merchant_category = random.choice(['gambling', 'crypto', 'electronics', 'travel'])
        else:
            # Normal transactions
            amount = random.uniform(100, 5000)  # Lower amounts
            account_age_days = random.randint(30, 1000)  # Older accounts
            past_24h_txn_count = random.randint(0, 5)  # Fewer transactions
            past_7d_avg_amount = random.uniform(500, 3000)
            is_night_txn = random.random() < 0.2  # Less likely at night
            is_new_device = random.random() < 0.1  # Less likely new device
            is_new_city = random.random() < 0.15  # Less likely new city
            merchant_category = random.choice(['retail', 'grocery', 'restaurant', 'fuel', 'utilities'])
        
        transaction = {
            'user_id': f'U{random.randint(1000, 9999)}',
            'amount': round(amount, 2),
            'timestamp': timestamp,
            'merchant_category': merchant_category,
            'device_id': f'D{random.randint(100, 999)}',
            'ip_city': random.choice(CITIES),
            'bank_name': random.choice(BANKS),
            'account_age_days': account_age_days,
            'past_24h_txn_count': past_24h_txn_count,
            'past_7d_avg_amount': round(past_7d_avg_amount, 2),
            'is_night_txn': int(is_night_txn),
            'is_new_device': int(is_new_device),
            'is_new_city': int(is_new_city),
            'is_fraud': int(is_fraud)
        }
        
        data.append(transaction)
    
    df = pd.DataFrame(data)
    
    # Add engineered features
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['amount_to_avg_ratio'] = df['amount'] / df['past_7d_avg_amount']
    
    return df


def save_sample_data(df=None):
    """
    Save sample transaction data to CSV
    
    Args:
        df: DataFrame to save (if None, generates new data)
    """
    if df is None:
        df = generate_synthetic_data()
    
    df.to_csv(SAMPLE_DATA_PATH, index=False)
    print(f"Saved {len(df)} transactions to {SAMPLE_DATA_PATH}")
    print(f"Fraud rate: {df['is_fraud'].mean()*100:.1f}%")
    
    return df


def load_sample_data():
    """Load sample transaction data from CSV"""
    if not SAMPLE_DATA_PATH.exists():
        print("Sample data not found. Generating...")
        return save_sample_data()
    
    df = pd.read_csv(SAMPLE_DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def save_scored_transactions(df, output_path):
    """
    Save scored transactions to CSV
    
    Args:
        df: DataFrame with scored transactions
        output_path: Path to save file
    """
    df.to_csv(output_path, index=False)
    print(f"Saved scored transactions to {output_path}")
