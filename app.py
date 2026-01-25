"""
FraudShield AI - Transaction Fraud Risk Engine
Production-grade fraud detection system
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

from src.scorer import FraudScorer
from src.explainability import generate_explanation, format_explanation_text
from src.simulator import TransactionSimulator
from src.storage import load_sample_data, save_sample_data, save_scored_transactions, generate_synthetic_data
from src.model import FraudModel
from src.config import MERCHANT_CATEGORIES, BANKS, CITIES, MODEL_FEATURES
from src.ui import apply_custom_css, display_score_card, display_alert, display_metric

# Page configuration
st.set_page_config(
    page_title="FraudShield AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styling
apply_custom_css()

# Initialize session state
if 'scorer' not in st.session_state:
    st.session_state.scorer = FraudScorer()

if 'simulator' not in st.session_state:
    st.session_state.simulator = TransactionSimulator()

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x60/667eea/ffffff?text=FraudShield+AI", width=200)
    st.markdown("### Transaction Fraud Risk Engine")
    st.markdown("---")
    
    # Model status
    if st.session_state.scorer.model_loaded:
        st.success("✓ ML Model Loaded")
    else:
        st.warning("⚠ ML Model Not Available")
        if st.button("Train Model Now"):
            with st.spinner("Training model on sample data..."):
                # Load or generate data
                try:
                    df = load_sample_data()
                except:
                    df = save_sample_data()
                
                # Train model
                train_score, test_score = st.session_state.scorer.train_model(df)
                st.success(f"Model trained! Test accuracy: {test_score:.3f}")
                st.rerun()
    
    st.markdown("---")
    st.markdown("**About**")
    st.markdown("Real-time fraud detection using hybrid Rules + ML engine")
    st.markdown("Version 1.0.0")

# Main content
st.title("🛡️ FraudShield AI")
st.markdown("### Production-Grade Transaction Fraud Risk Engine")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Live Scoring",
    "📊 Batch Analyzer",
    "🔮 What-If Simulator",
    "📈 Risk Analytics"
])

# ============================================
# TAB 1: Live Scoring
# ============================================
with tab1:
    st.markdown("## Transaction Risk Assessment")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Transaction Details")
        
        # Input form
        with st.form("transaction_form"):
            user_id = st.text_input("User ID", value="U1234", help="Unique user identifier")
            
            col_a, col_b = st.columns(2)
            with col_a:
                amount = st.number_input("Amount (₹)", min_value=0.0, value=5000.0, step=100.0)
                merchant_category = st.selectbox("Merchant Category", MERCHANT_CATEGORIES)
                bank_name = st.selectbox("Bank", BANKS)
                account_age_days = st.number_input("Account Age (days)", min_value=0, value=180, step=1)
            
            with col_b:
                device_id = st.text_input("Device ID", value="D123")
                ip_city = st.selectbox("City", CITIES)
                past_24h_txn_count = st.number_input("Transactions (24h)", min_value=0, value=2, step=1)
                past_7d_avg_amount = st.number_input("7-Day Avg Amount (₹)", min_value=0.0, value=2000.0, step=100.0)
            
            col_c, col_d, col_e = st.columns(3)
            with col_c:
                is_night_txn = st.checkbox("Night Transaction", value=False)
            with col_d:
                is_new_device = st.checkbox("New Device", value=False)
            with col_e:
                is_new_city = st.checkbox("New City", value=False)
            
            submitted = st.form_submit_button("🔍 Analyze Transaction", use_container_width=True)
        
        if submitted:
            # Create transaction
            transaction = {
                'user_id': user_id,
                'amount': amount,
                'timestamp': datetime.now(),
                'merchant_category': merchant_category,
                'device_id': device_id,
                'ip_city': ip_city,
                'bank_name': bank_name,
                'account_age_days': account_age_days,
                'past_24h_txn_count': past_24h_txn_count,
                'past_7d_avg_amount': past_7d_avg_amount,
                'is_night_txn': int(is_night_txn),
                'is_new_device': int(is_new_device),
                'is_new_city': int(is_new_city)
            }
            
            # Score transaction
            result = st.session_state.scorer.score(transaction)
            st.session_state.last_result = result
            st.session_state.last_transaction = transaction
    
    with col2:
        st.markdown("### Risk Assessment")
        
        if 'last_result' in st.session_state:
            result = st.session_state.last_result
            
            # Display score
            display_score_card(
                int(result['final_score']),
                result['risk_label'],
                result['risk_color']
            )
            
            # Score breakdown
            st.markdown("#### Score Breakdown")
            col_ml, col_rules = st.columns(2)
            with col_ml:
                display_metric(f"{result['ml_score']:.1f}", "ML Score")
            with col_rules:
                display_metric(f"{result['rules_score']:.1f}", "Rules Score")
            
            # Explanation
            st.markdown("#### Risk Explanation")
            explanation = generate_explanation(result)
            
            if result['final_score'] >= 60:
                display_alert(explanation['main_explanation'], 'danger')
            elif result['final_score'] >= 30:
                display_alert(explanation['main_explanation'], 'warning')
            else:
                display_alert(explanation['main_explanation'], 'success')
            
            st.markdown(f"**{explanation['summary']}**")
            
            if explanation['risk_factors']:
                st.markdown("**Key Risk Indicators:**")
                for factor in explanation['risk_factors']:
                    st.markdown(factor)
            else:
                st.info("No significant risk indicators detected")
            
            st.markdown(f"*{explanation['ml_contribution']}*")
            
            # Triggered rules details
            if result['triggered_rules']:
                with st.expander("🔍 View Detailed Rule Analysis"):
                    for rule in result['triggered_rules']:
                        st.markdown(f"**{rule['rule']}** (Risk: +{rule['risk_contribution']:.0f})")
                        st.markdown(f"*{rule['description']}*")
                        st.markdown("---")
        else:
            st.info("👆 Enter transaction details and click 'Analyze Transaction' to see risk assessment")

# ============================================
# TAB 2: Batch Analyzer
# ============================================
with tab2:
    st.markdown("## Batch Transaction Analysis")
    
    st.markdown("Upload a CSV file with transactions to score them in batch")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=['csv'],
            help="CSV must contain required columns: user_id, amount, merchant_category, etc."
        )
        
        if uploaded_file is not None:
            try:
                df_batch = pd.read_csv(uploaded_file)
                st.success(f"✓ Loaded {len(df_batch)} transactions")
                
                # Show preview
                with st.expander("Preview Data"):
                    st.dataframe(df_batch.head(10), use_container_width=True)
                
                if st.button("🚀 Score All Transactions", use_container_width=True):
                    with st.spinner("Scoring transactions..."):
                        # Score each transaction
                        scores = []
                        risk_labels = []
                        
                        for idx, row in df_batch.iterrows():
                            transaction = row.to_dict()
                            if 'timestamp' not in transaction:
                                transaction['timestamp'] = datetime.now()
                            
                            result = st.session_state.scorer.score(transaction)
                            scores.append(result['final_score'])
                            risk_labels.append(result['risk_label'])
                        
                        df_batch['fraud_score'] = scores
                        df_batch['risk_label'] = risk_labels
                        
                        st.session_state.scored_batch = df_batch
                        st.success("✓ Scoring complete!")
            
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
        else:
            # Use sample data
            st.info("Or use sample data to test:")
            if st.button("Load Sample Transactions"):
                try:
                    df_batch = load_sample_data()
                except:
                    df_batch = save_sample_data()
                
                st.session_state.sample_batch = df_batch
                st.success(f"✓ Loaded {len(df_batch)} sample transactions")
    
    with col2:
        if 'scored_batch' in st.session_state:
            df_scored = st.session_state.scored_batch
            
            st.markdown("### Results Summary")
            
            # Summary metrics
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                display_metric(len(df_scored), "Total Transactions")
            with col_b:
                high_risk = len(df_scored[df_scored['risk_label'] == 'High Risk'])
                display_metric(high_risk, "High Risk")
            with col_c:
                avg_score = df_scored['fraud_score'].mean()
                display_metric(f"{avg_score:.1f}", "Avg Score")
            
            # Flagged transactions
            st.markdown("### High-Risk Transactions")
            high_risk_df = df_scored[df_scored['risk_label'] == 'High Risk'].sort_values('fraud_score', ascending=False)
            
            if len(high_risk_df) > 0:
                st.dataframe(
                    high_risk_df[['user_id', 'amount', 'merchant_category', 'fraud_score', 'risk_label']].head(10),
                    use_container_width=True
                )
            else:
                st.success("No high-risk transactions detected!")
            
            # Download scored CSV
            st.markdown("### Export Results")
            csv_buffer = BytesIO()
            df_scored.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            st.download_button(
                label="📥 Download Scored Transactions (CSV)",
                data=csv_buffer,
                file_name=f"scored_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        elif 'sample_batch' in st.session_state:
            st.info("Click 'Score All Transactions' in the Batch Analyzer to process the loaded data")

# ============================================
# TAB 3: What-If Simulator
# ============================================
with tab3:
    st.markdown("## What-If Transaction Simulator")
    st.markdown("Explore how changes in transaction parameters affect the fraud risk score")
    
    if 'last_transaction' not in st.session_state:
        st.warning("⚠ Please score a transaction in the Live Scoring tab first")
    else:
        base_txn = st.session_state.last_transaction
        
        # Set base transaction for simulator
        base_result = st.session_state.simulator.set_base_transaction(base_txn)
        base_score = base_result['final_score']
        
        st.info(f"**Base Transaction Score:** {base_score:.1f} ({base_result['risk_label']})")
        
        st.markdown("### Adjust Parameters")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Simulate amount change
            st.markdown("#### Amount")
            sim_amount = st.slider(
                "Transaction Amount (₹)",
                min_value=100.0,
                max_value=50000.0,
                value=float(base_txn['amount']),
                step=500.0
            )
            
            # Simulate velocity change
            st.markdown("#### Transaction Velocity")
            sim_velocity = st.slider(
                "Transactions in 24h",
                min_value=0,
                max_value=30,
                value=int(base_txn['past_24h_txn_count']),
                step=1
            )
            
            # Boolean flags
            st.markdown("#### Risk Flags")
            sim_new_device = st.checkbox("New Device", value=bool(base_txn['is_new_device']))
            sim_new_city = st.checkbox("New City", value=bool(base_txn['is_new_city']))
            sim_night_txn = st.checkbox("Night Transaction", value=bool(base_txn['is_night_txn']))
        
        with col2:
            # Simulate the changes
            changes = {
                'amount': sim_amount,
                'past_24h_txn_count': sim_velocity,
                'is_new_device': int(sim_new_device),
                'is_new_city': int(sim_new_city),
                'is_night_txn': int(sim_night_txn)
            }
            
            sim_result = st.session_state.simulator.simulate_multiple_changes(changes)
            new_score = sim_result['new_score']
            score_delta = sim_result['score_delta']
            
            # Display new score
            st.markdown("#### Simulated Risk Score")
            display_score_card(
                int(new_score),
                sim_result['new_result']['risk_label'],
                sim_result['new_result']['risk_color']
            )
            
            # Show delta
            if score_delta > 0:
                st.error(f"📈 Score increased by {score_delta:.1f} points")
            elif score_delta < 0:
                st.success(f"📉 Score decreased by {abs(score_delta):.1f} points")
            else:
                st.info("Score unchanged")
            
            # Rule changes
            rule_changes = st.session_state.simulator.get_rule_changes(base_result, sim_result['new_result'])
            
            if rule_changes['added']:
                st.warning(f"**New Rules Triggered:** {', '.join(rule_changes['added'])}")
            
            if rule_changes['removed']:
                st.success(f"**Rules Cleared:** {', '.join(rule_changes['removed'])}")
            
            # Show new explanation
            with st.expander("View Updated Risk Explanation"):
                new_explanation = generate_explanation(sim_result['new_result'])
                st.markdown(format_explanation_text(new_explanation))

# ============================================
# TAB 4: Risk Analytics
# ============================================
with tab4:
    st.markdown("## Risk Analytics Dashboard")
    
    # Load data for analytics
    try:
        df_analytics = load_sample_data()
    except:
        df_analytics = save_sample_data()
    
    # Score transactions if not already scored
    if 'fraud_score' not in df_analytics.columns:
        with st.spinner("Scoring transactions for analytics..."):
            scores = []
            for idx, row in df_analytics.iterrows():
                transaction = row.to_dict()
                result = st.session_state.scorer.score(transaction)
                scores.append(result['final_score'])
            df_analytics['fraud_score'] = scores
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_txns = len(df_analytics)
        display_metric(f"{total_txns:,}", "Total Transactions")
    
    with col2:
        high_risk = len(df_analytics[df_analytics['fraud_score'] >= 60])
        display_metric(high_risk, "High Risk Count")
    
    with col3:
        avg_score = df_analytics['fraud_score'].mean()
        display_metric(f"{avg_score:.1f}", "Average Score")
    
    with col4:
        if 'is_fraud' in df_analytics.columns:
            fraud_rate = df_analytics['is_fraud'].mean() * 100
            display_metric(f"{fraud_rate:.1f}%", "Fraud Rate")
    
    st.markdown("---")
    
    # Charts
    col_left, col_right = st.columns(2)
    
    with col_left:
        # Risk distribution
        st.markdown("### Risk Score Distribution")
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(df_analytics['fraud_score'], bins=30, color='#667eea', alpha=0.7, edgecolor='black')
        ax.axvline(30, color='green', linestyle='--', label='Low/Medium threshold')
        ax.axvline(60, color='red', linestyle='--', label='Medium/High threshold')
        ax.set_xlabel('Fraud Risk Score')
        ax.set_ylabel('Number of Transactions')
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        
        # Top risky merchant categories
        st.markdown("### Top Risky Merchant Categories")
        merchant_risk = df_analytics.groupby('merchant_category')['fraud_score'].mean().sort_values(ascending=False).head(8)
        fig, ax = plt.subplots(figsize=(8, 5))
        merchant_risk.plot(kind='barh', ax=ax, color='#f59e0b')
        ax.set_xlabel('Average Fraud Score')
        ax.set_ylabel('Merchant Category')
        ax.grid(True, alpha=0.3, axis='x')
        st.pyplot(fig)
    
    with col_right:
        # High-risk transactions by city
        st.markdown("### High-Risk Transactions by City")
        city_high_risk = df_analytics[df_analytics['fraud_score'] >= 60].groupby('ip_city').size().sort_values(ascending=False).head(10)
        fig, ax = plt.subplots(figsize=(8, 5))
        city_high_risk.plot(kind='bar', ax=ax, color='#ef4444')
        ax.set_xlabel('City')
        ax.set_ylabel('High-Risk Transaction Count')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        st.pyplot(fig)
        
        # Risk by hour of day
        st.markdown("### Risk Score by Hour of Day")
        if 'hour_of_day' in df_analytics.columns:
            hourly_risk = df_analytics.groupby('hour_of_day')['fraud_score'].mean()
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(hourly_risk.index, hourly_risk.values, marker='o', linewidth=2, color='#667eea')
            ax.fill_between(hourly_risk.index, hourly_risk.values, alpha=0.3, color='#667eea')
            ax.set_xlabel('Hour of Day')
            ax.set_ylabel('Average Fraud Score')
            ax.set_xticks(range(0, 24, 2))
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #6b7280; font-size: 0.875rem;'>"
    "FraudShield AI v1.0.0 | Production-Grade Transaction Fraud Risk Engine"
    "</div>",
    unsafe_allow_html=True
)
