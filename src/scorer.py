"""
Hybrid fraud scoring engine (Rules + ML)
"""
from src.rules_engine import RulesEngine
from src.model import FraudModel
from src.features import extract_features
from src.config import ML_WEIGHT, RULES_WEIGHT


class FraudScorer:
    """Hybrid fraud scoring combining rules and ML"""
    
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.ml_model = FraudModel()
        self.model_loaded = False
        
        # Try to load existing model
        try:
            if self.ml_model.exists():
                self.ml_model.load()
                self.model_loaded = True
        except Exception as e:
            print(f"Could not load ML model: {e}")
            self.model_loaded = False
    
    def score(self, transaction):
        """
        Calculate fraud risk score for a transaction
        
        Args:
            transaction: Dictionary of transaction data
            
        Returns:
            Dictionary with score, label, and components
        """
        # Extract features
        features = extract_features(transaction)
        
        # Get rules score
        rules_score, triggered_rules = self.rules_engine.evaluate(features)
        
        # Get ML score
        if self.model_loaded:
            try:
                ml_prob = self.ml_model.predict_proba(features)
                ml_score = ml_prob * 100  # Convert to 0-100 scale
            except Exception as e:
                print(f"ML prediction error: {e}")
                ml_score = 50  # Default if error
                ml_prob = 0.5
        else:
            # Fallback if no model
            ml_score = 50
            ml_prob = 0.5
        
        # Combine scores (weighted average)
        final_score = (ML_WEIGHT * ml_score) + (RULES_WEIGHT * rules_score)
        final_score = min(100, max(0, final_score))
        
        # Determine risk label
        if final_score < 30:
            risk_label = "Low Risk"
            risk_color = "green"
        elif final_score < 60:
            risk_label = "Medium Risk"
            risk_color = "orange"
        else:
            risk_label = "High Risk"
            risk_color = "red"
        
        return {
            'final_score': round(final_score, 2),
            'risk_label': risk_label,
            'risk_color': risk_color,
            'ml_score': round(ml_score, 2),
            'ml_probability': round(ml_prob, 4),
            'rules_score': round(rules_score, 2),
            'triggered_rules': triggered_rules,
            'features': features
        }
    
    def train_model(self, df):
        """Train the ML model"""
        train_score, test_score = self.ml_model.train(df)
        self.ml_model.save()
        self.model_loaded = True
        return train_score, test_score
