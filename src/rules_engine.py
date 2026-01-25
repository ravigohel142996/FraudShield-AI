"""
Rules-based fraud detection engine
"""


class RulesEngine:
    """Rule-based fraud detection"""
    
    def __init__(self):
        self.triggered_rules = []
        
    def evaluate(self, features):
        """
        Evaluate all fraud rules on a transaction
        
        Args:
            features: Dictionary of transaction features
            
        Returns:
            tuple: (risk_score, list of triggered rules)
        """
        self.triggered_rules = []
        total_risk = 0
        
        # Rule 1: Velocity rule - too many transactions quickly
        if features.get('past_24h_txn_count', 0) > 10:
            risk = min(30, features['past_24h_txn_count'] * 2)
            total_risk += risk
            self.triggered_rules.append({
                'rule': 'High Velocity',
                'description': f"{features['past_24h_txn_count']} transactions in 24h (threshold: 10)",
                'risk_contribution': risk
            })
        
        # Rule 2: Amount spike - transaction much higher than baseline
        amount_ratio = features.get('amount_to_avg_ratio', 1)
        if amount_ratio > 3:
            risk = min(25, (amount_ratio - 3) * 5)
            total_risk += risk
            self.triggered_rules.append({
                'rule': 'Amount Spike',
                'description': f"Amount {amount_ratio:.1f}x higher than 7-day average (threshold: 3x)",
                'risk_contribution': risk
            })
        
        # Rule 3: New device + high amount
        if features.get('is_new_device', 0) == 1 and features.get('amount', 0) > 10000:
            risk = 20
            total_risk += risk
            self.triggered_rules.append({
                'rule': 'New Device + High Amount',
                'description': f"First transaction from this device with ₹{features['amount']:,.0f}",
                'risk_contribution': risk
            })
        
        # Rule 4: New city + night transaction
        if features.get('is_new_city', 0) == 1 and features.get('is_night_txn', 0) == 1:
            risk = 15
            total_risk += risk
            self.triggered_rules.append({
                'rule': 'New Location + Night Transaction',
                'description': "First transaction from this city during night hours (10 PM - 6 AM)",
                'risk_contribution': risk
            })
        
        # Rule 5: Very new account with high transaction
        if features.get('account_age_days', 0) < 7 and features.get('amount', 0) > 5000:
            risk = 20
            total_risk += risk
            self.triggered_rules.append({
                'rule': 'New Account Risk',
                'description': f"Account only {features['account_age_days']} days old with ₹{features['amount']:,.0f} transaction",
                'risk_contribution': risk
            })
        
        # Rule 6: Night transaction with high amount
        if features.get('is_night_txn', 0) == 1 and features.get('amount', 0) > 20000:
            risk = 15
            total_risk += risk
            self.triggered_rules.append({
                'rule': 'High Night Transaction',
                'description': f"₹{features['amount']:,.0f} transaction during night hours",
                'risk_contribution': risk
            })
        
        # Rule 7: Multiple risk factors combined
        risk_factor_count = sum([
            features.get('is_new_device', 0),
            features.get('is_new_city', 0),
            features.get('is_night_txn', 0),
            1 if features.get('past_24h_txn_count', 0) > 5 else 0
        ])
        if risk_factor_count >= 3:
            risk = 10
            total_risk += risk
            self.triggered_rules.append({
                'rule': 'Multiple Risk Factors',
                'description': f"{risk_factor_count} simultaneous risk indicators detected",
                'risk_contribution': risk
            })
        
        # Cap at 100
        risk_score = min(100, total_risk)
        
        return risk_score, self.triggered_rules
    
    def get_triggered_rules(self):
        """Get list of triggered rules"""
        return self.triggered_rules
