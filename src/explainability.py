"""
Explainability module for fraud predictions
"""


def generate_explanation(score_result):
    """
    Generate human-readable explanation for fraud score
    
    Args:
        score_result: Dictionary from FraudScorer.score()
        
    Returns:
        Dictionary with explanation components
    """
    triggered_rules = score_result.get('triggered_rules', [])
    features = score_result.get('features', {})
    ml_prob = score_result.get('ml_probability', 0)
    
    # Get top 3 triggered rules
    top_rules = sorted(triggered_rules, key=lambda x: x['risk_contribution'], reverse=True)[:3]
    
    # Build explanation text
    if score_result['risk_label'] == "Low Risk":
        main_explanation = "Transaction appears legitimate with minimal risk indicators."
    elif score_result['risk_label'] == "Medium Risk":
        main_explanation = "Transaction shows some suspicious patterns that warrant review."
    else:
        main_explanation = "Transaction exhibits multiple high-risk characteristics."
    
    # List risk factors
    risk_factors = []
    for rule in top_rules:
        risk_factors.append(f"• {rule['description']}")
    
    # Identify top contributing features
    feature_contributions = []
    
    if features.get('is_new_device', 0) == 1:
        feature_contributions.append("New device")
    
    if features.get('is_new_city', 0) == 1:
        feature_contributions.append("New city")
    
    if features.get('is_night_txn', 0) == 1:
        feature_contributions.append("Night transaction")
    
    if features.get('amount_to_avg_ratio', 1) > 3:
        feature_contributions.append("Amount spike")
    
    if features.get('past_24h_txn_count', 0) > 10:
        feature_contributions.append("High velocity")
    
    if features.get('account_age_days', 0) < 7:
        feature_contributions.append("New account")
    
    # Build summary
    if feature_contributions:
        summary = f"Risk factors: {', '.join(feature_contributions)}"
    else:
        summary = "No major risk factors detected"
    
    return {
        'main_explanation': main_explanation,
        'summary': summary,
        'top_rules': top_rules,
        'risk_factors': risk_factors,
        'ml_contribution': f"ML model confidence: {ml_prob*100:.1f}%",
        'feature_count': len(feature_contributions)
    }


def format_explanation_text(explanation):
    """
    Format explanation as text
    
    Args:
        explanation: Dictionary from generate_explanation()
        
    Returns:
        Formatted text string
    """
    lines = [
        explanation['main_explanation'],
        "",
        explanation['summary'],
        "",
        "Key Risk Indicators:"
    ]
    
    for factor in explanation['risk_factors']:
        lines.append(factor)
    
    if not explanation['risk_factors']:
        lines.append("• No significant risk indicators")
    
    lines.append("")
    lines.append(explanation['ml_contribution'])
    
    return "\n".join(lines)
