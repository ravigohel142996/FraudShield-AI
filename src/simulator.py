"""
What-if simulation for transaction parameters
"""
from src.scorer import FraudScorer


class TransactionSimulator:
    """Simulate changes to transaction parameters"""
    
    def __init__(self):
        self.scorer = FraudScorer()
        self.base_transaction = None
        self.base_score = None
    
    def set_base_transaction(self, transaction):
        """Set the base transaction for simulation"""
        self.base_transaction = transaction.copy()
        result = self.scorer.score(self.base_transaction)
        self.base_score = result['final_score']
        return result
    
    def simulate_change(self, parameter, new_value):
        """
        Simulate changing a single parameter
        
        Args:
            parameter: Name of parameter to change
            new_value: New value for the parameter
            
        Returns:
            Dictionary with simulation results
        """
        if self.base_transaction is None:
            raise ValueError("Base transaction not set. Call set_base_transaction() first.")
        
        # Create modified transaction
        modified_transaction = self.base_transaction.copy()
        modified_transaction[parameter] = new_value
        
        # Score modified transaction
        new_result = self.scorer.score(modified_transaction)
        new_score = new_result['final_score']
        
        # Calculate delta
        score_delta = new_score - self.base_score
        
        # Determine impact
        if abs(score_delta) < 5:
            impact = "Minimal"
        elif abs(score_delta) < 15:
            impact = "Moderate"
        else:
            impact = "Significant"
        
        return {
            'parameter': parameter,
            'old_value': self.base_transaction.get(parameter),
            'new_value': new_value,
            'base_score': self.base_score,
            'new_score': new_score,
            'score_delta': score_delta,
            'impact': impact,
            'new_result': new_result
        }
    
    def simulate_multiple_changes(self, changes):
        """
        Simulate multiple parameter changes at once
        
        Args:
            changes: Dictionary of parameter: new_value pairs
            
        Returns:
            Dictionary with simulation results
        """
        if self.base_transaction is None:
            raise ValueError("Base transaction not set. Call set_base_transaction() first.")
        
        # Create modified transaction
        modified_transaction = self.base_transaction.copy()
        for param, value in changes.items():
            modified_transaction[param] = value
        
        # Score modified transaction
        new_result = self.scorer.score(modified_transaction)
        new_score = new_result['final_score']
        
        # Calculate delta
        score_delta = new_score - self.base_score
        
        return {
            'changes': changes,
            'base_score': self.base_score,
            'new_score': new_score,
            'score_delta': score_delta,
            'new_result': new_result
        }
    
    def get_rule_changes(self, base_result, new_result):
        """
        Compare triggered rules between base and new result
        
        Args:
            base_result: Result from base transaction
            new_result: Result from modified transaction
            
        Returns:
            Dictionary with rule changes
        """
        base_rules = set([r['rule'] for r in base_result.get('triggered_rules', [])])
        new_rules = set([r['rule'] for r in new_result.get('triggered_rules', [])])
        
        added_rules = new_rules - base_rules
        removed_rules = base_rules - new_rules
        
        return {
            'added': list(added_rules),
            'removed': list(removed_rules),
            'unchanged': list(base_rules & new_rules)
        }
