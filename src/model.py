"""
ML model training and prediction
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path

from src.config import MODEL_PATH, SCALER_PATH, MODEL_FEATURES


class FraudModel:
    """Machine learning model for fraud detection"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = MODEL_FEATURES
        self.is_trained = False
        
    def train(self, df):
        """
        Train the fraud detection model
        
        Args:
            df: DataFrame with transaction data and 'is_fraud' label
        """
        # Prepare features
        X = df[self.feature_names].values
        y = df['is_fraud'].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            class_weight='balanced'
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        print(f"Model trained - Train accuracy: {train_score:.3f}, Test accuracy: {test_score:.3f}")
        
        self.is_trained = True
        
        return train_score, test_score
    
    def predict_proba(self, features):
        """
        Predict fraud probability
        
        Args:
            features: Dictionary of transaction features
            
        Returns:
            Fraud probability (0-1)
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Call train() first or load() existing model.")
        
        # Prepare feature vector
        feature_vector = np.array([[features.get(name, 0) for name in self.feature_names]])
        
        # Scale
        feature_vector_scaled = self.scaler.transform(feature_vector)
        
        # Predict probability of fraud (class 1)
        prob = self.model.predict_proba(feature_vector_scaled)[0][1]
        
        return prob
    
    def get_feature_importance(self):
        """Get feature importance from the model"""
        if not self.is_trained:
            return {}
        
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def save(self):
        """Save model and scaler to disk"""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        joblib.dump(self.model, MODEL_PATH)
        joblib.dump(self.scaler, SCALER_PATH)
        print(f"Model saved to {MODEL_PATH}")
        print(f"Scaler saved to {SCALER_PATH}")
    
    def load(self):
        """Load model and scaler from disk"""
        if not MODEL_PATH.exists() or not SCALER_PATH.exists():
            raise FileNotFoundError("Model or scaler file not found")
        
        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)
        self.is_trained = True
        print("Model and scaler loaded successfully")
        
    def exists(self):
        """Check if saved model exists"""
        return MODEL_PATH.exists() and SCALER_PATH.exists()
