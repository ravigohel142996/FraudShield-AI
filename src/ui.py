"""
UI helper functions and styling
"""
import streamlit as st


def apply_custom_css():
    """Apply custom CSS for professional UI"""
    st.markdown("""
        <style>
        /* Main theme */
        .main {
            background-color: #f8f9fa;
        }
        
        /* Card styling */
        .risk-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1rem;
        }
        
        /* Score display */
        .score-display {
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            color: white;
            margin-bottom: 1rem;
        }
        
        .score-number {
            font-size: 4rem;
            font-weight: bold;
            margin: 0;
        }
        
        .score-label {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-top: 0.5rem;
        }
        
        /* Risk labels */
        .risk-low {
            color: #10b981;
            font-weight: 600;
        }
        
        .risk-medium {
            color: #f59e0b;
            font-weight: 600;
        }
        
        .risk-high {
            color: #ef4444;
            font-weight: 600;
        }
        
        /* Alert boxes */
        .alert-box {
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid;
        }
        
        .alert-info {
            background-color: #dbeafe;
            border-color: #3b82f6;
            color: #1e40af;
        }
        
        .alert-warning {
            background-color: #fef3c7;
            border-color: #f59e0b;
            color: #92400e;
        }
        
        .alert-danger {
            background-color: #fee2e2;
            border-color: #ef4444;
            color: #991b1b;
        }
        
        /* Metric cards */
        .metric-card {
            background: white;
            padding: 1.25rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #1f2937;
        }
        
        .metric-label {
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 0.25rem;
        }
        
        /* Table styling */
        .dataframe {
            font-size: 0.875rem;
        }
        
        /* Header styling */
        h1 {
            color: #1f2937;
            font-weight: 700;
        }
        
        h2 {
            color: #374151;
            font-weight: 600;
            margin-top: 2rem;
        }
        
        h3 {
            color: #4b5563;
            font-weight: 600;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #1f2937;
        }
        
        /* Button styling */
        .stButton>button {
            background-color: #667eea;
            color: white;
            border-radius: 8px;
            padding: 0.5rem 2rem;
            font-weight: 600;
            border: none;
            transition: all 0.3s;
        }
        
        .stButton>button:hover {
            background-color: #5568d3;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        /* Input styling */
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input,
        .stSelectbox>div>div>select {
            border-radius: 8px;
            border: 1px solid #d1d5db;
        }
        
        /* Remove default streamlit padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)


def display_score_card(score, label, color):
    """Display fraud score in a card"""
    color_map = {
        'green': '#10b981',
        'orange': '#f59e0b',
        'red': '#ef4444'
    }
    bg_color = color_map.get(color, '#667eea')
    
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, {bg_color} 0%, {bg_color}dd 100%);
                    padding: 2rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 1.5rem;">
            <div style="font-size: 4rem; font-weight: bold;">{score}</div>
            <div style="font-size: 1.2rem; margin-top: 0.5rem;">{label}</div>
        </div>
    """, unsafe_allow_html=True)


def display_alert(message, alert_type='info'):
    """Display an alert box"""
    type_config = {
        'info': {'bg': '#dbeafe', 'border': '#3b82f6', 'text': '#1e40af'},
        'warning': {'bg': '#fef3c7', 'border': '#f59e0b', 'text': '#92400e'},
        'danger': {'bg': '#fee2e2', 'border': '#ef4444', 'text': '#991b1b'},
        'success': {'bg': '#d1fae5', 'border': '#10b981', 'text': '#065f46'}
    }
    
    config = type_config.get(alert_type, type_config['info'])
    
    st.markdown(f"""
        <div style="background-color: {config['bg']}; 
                    border-left: 4px solid {config['border']}; 
                    color: {config['text']};
                    padding: 1rem; 
                    border-radius: 8px; 
                    margin: 1rem 0;">
            {message}
        </div>
    """, unsafe_allow_html=True)


def display_metric(value, label):
    """Display a metric card"""
    st.markdown(f"""
        <div style="background: white; padding: 1.25rem; border-radius: 8px; 
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;">
            <div style="font-size: 2rem; font-weight: bold; color: #1f2937;">{value}</div>
            <div style="font-size: 0.875rem; color: #6b7280; margin-top: 0.25rem;">{label}</div>
        </div>
    """, unsafe_allow_html=True)
