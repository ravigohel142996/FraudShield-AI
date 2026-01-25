"""
Feature engineering for fraud detection
"""
import pandas as pd
from datetime import datetime


def extract_features(transaction_dict):
    """
    Extract and engineer features from a transaction
    
    Args:
        transaction_dict: Dictionary containing transaction data
        
    Returns:
        Dictionary with engineered features
    """
    features = transaction_dict.copy()
    
    # Parse timestamp if it's a string
    if isinstance(features.get('timestamp'), str):
        try:
            timestamp = pd.to_datetime(features['timestamp'])
        except:
            timestamp = datetime.now()
    else:
        timestamp = features.get('timestamp', datetime.now())
    
    # Extract hour of day
    features['hour_of_day'] = timestamp.hour
    
    # Calculate amount to average ratio
    amount = float(features.get('amount', 0))
    avg_amount = float(features.get('past_7d_avg_amount', 1))
    features['amount_to_avg_ratio'] = amount / max(avg_amount, 1)
    
    # Ensure boolean fields are integers
    features['is_night_txn'] = int(features.get('is_night_txn', 0))
    features['is_new_device'] = int(features.get('is_new_device', 0))
    features['is_new_city'] = int(features.get('is_new_city', 0))
    
    # Ensure numeric fields
    features['account_age_days'] = int(features.get('account_age_days', 0))
    features['past_24h_txn_count'] = int(features.get('past_24h_txn_count', 0))
    features['past_7d_avg_amount'] = float(features.get('past_7d_avg_amount', 0))
    
    return features


def prepare_model_input(features, feature_names):
    """
    Prepare feature vector for model input
    
    Args:
        features: Dictionary of features
        feature_names: List of feature names expected by model
        
    Returns:
        List of feature values in correct order
    """
    return [features.get(name, 0) for name in feature_names]
