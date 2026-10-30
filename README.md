# 🛡️ FraudShield AI - Transaction Fraud Risk Engine

A production-grade fraud detection system that combines rule-based logic with machine learning to score transactions (0-100) and provide comprehensive explanations for fraud risk assessment.

---

> **Note (2026-10-30):** This repository also contains
> **[`RAGShield-Eval/`](RAGShield-Eval/README.md)** — a separate, self-contained project
> submitted to the **micro1 Eval Hackathon 2026**: a reproducible benchmark for indirect
> prompt injection and retrieval authorisation in RAG systems. It shares no code with
> FraudShield AI, which is unaffected. Start at `RAGShield-Eval/README.md`.

## 🎯 Problem Statement

Financial institutions and payment processors need real-time fraud detection systems that can:
- Score transactions instantly with high accuracy
- Provide clear explanations for fraud decisions
- Allow risk analysts to simulate "what-if" scenarios
- Process transactions in batch mode
- Provide analytics and insights on fraud patterns

FraudShield AI addresses these needs with a hybrid approach combining deterministic rules and machine learning.

## ✨ Features

### 1. **Hybrid Fraud Detection Engine**
- **Rules Engine**: Deterministic fraud rules covering:
  - High velocity attacks (too many transactions in 24h)
  - Amount spike detection (transaction >> user baseline)
  - New device + high amount combinations
  - New location + night transaction patterns
  - New account risk assessment
  - Multiple simultaneous risk factors
  
- **Machine Learning Model**: 
  - Random Forest classifier trained on synthetic transaction data
  - Feature importance analysis
  - Probability-based scoring
  
- **Weighted Scoring**: 60% ML + 40% Rules = Final Risk Score (0-100)

### 2. **Explainability & Transparency**
- Top 3 rule triggers with descriptions
- ML probability confidence
- Feature-level contribution analysis
- Human-readable risk explanations
- Color-coded risk levels (Low/Medium/High)

### 3. **Live Transaction Scoring**
- Real-time fraud risk assessment
- Interactive input form with 13+ transaction parameters
- Instant score calculation with detailed breakdown
- Visual risk indicators

### 4. **Batch Transaction Analyzer**
- CSV file upload support
- Bulk transaction scoring
- High-risk transaction flagging
- Export scored results as CSV
- Summary statistics and metrics

### 5. **What-If Simulator**
- Interactive parameter adjustment
- Real-time score recalculation
- Delta analysis (score change visualization)
- Rule trigger/clear notifications
- Scenario testing capability

### 6. **Risk Analytics Dashboard**
- Transaction volume metrics
- Risk score distribution histogram
- Top risky merchant categories
- High-risk city analysis
- Hourly risk trends
- Fraud rate statistics

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Transaction Input                   │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │    Feature Engineering       │
        │  (extract & transform)       │
        └──────────┬──────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────┐    ┌──────────────────┐
│ Rules Engine │    │   ML Model       │
│ (40% weight) │    │ (60% weight)     │
└──────┬───────┘    └────────┬─────────┘
       │                     │
       └──────────┬──────────┘
                  ▼
         ┌────────────────┐
         │ Hybrid Scorer  │
         │  (0-100 scale) │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │ Explainability │
         │    Engine      │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │  UI Display    │
         └────────────────┘
```

## 📊 Input Features

| Feature | Type | Description |
|---------|------|-------------|
| `user_id` | String | Unique user identifier |
| `amount` | Float | Transaction amount (₹) |
| `timestamp` | Datetime | Transaction timestamp |
| `merchant_category` | String | Category (retail, gambling, crypto, etc.) |
| `device_id` | String | Device identifier |
| `ip_city` | String | Transaction city |
| `bank_name` | String | User's bank |
| `account_age_days` | Integer | Account age in days |
| `past_24h_txn_count` | Integer | Transactions in last 24 hours |
| `past_7d_avg_amount` | Float | Average amount over 7 days |
| `is_night_txn` | Boolean | Night transaction (10 PM - 6 AM) |
| `is_new_device` | Boolean | First transaction from device |
| `is_new_city` | Boolean | First transaction from city |

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/ravigohel142996/FraudShield-AI.git
cd FraudShield-AI
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
streamlit run app.py
```

5. **Access the app**
Open your browser to `http://localhost:8501`

### First-Time Setup

On first run, the application will:
1. Generate 10,000 synthetic transactions (if data doesn't exist)
2. Train the ML model automatically
3. Save model artifacts to `data/trained/`

You can also manually trigger model training from the sidebar.

## 🌐 Deployment on Render

1. **Fork this repository** to your GitHub account

2. **Create a new Web Service** on [Render](https://render.com)

3. **Connect your repository**

4. **Configure the service**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port 10000 --server.address 0.0.0.0`
   - **Environment**: Python 3.11

5. **Deploy** - Render will automatically deploy using `render.yaml`

The app will be live at your Render URL (e.g., `https://fraudshield-ai.onrender.com`)

## 📁 Project Structure

```
FraudShield-AI/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment config
├── README.md                   # Documentation
├── .gitignore                  # Git ignore rules
│
├── data/
│   ├── sample_transactions.csv # Synthetic dataset (10k rows)
│   └── trained/
│       ├── model.pkl          # Trained ML model
│       └── scaler.pkl         # Feature scaler
│
└── src/
    ├── __init__.py            # Package initialization
    ├── config.py              # Configuration & constants
    ├── features.py            # Feature engineering
    ├── rules_engine.py        # Rule-based detection
    ├── model.py               # ML model training/prediction
    ├── scorer.py              # Hybrid scoring engine
    ├── explainability.py      # Explanation generation
    ├── simulator.py           # What-if simulation
    ├── storage.py             # Data persistence
    └── ui.py                  # UI helper functions
```

## 🔧 Configuration

Key configuration in `src/config.py`:

```python
# Scoring weights
ML_WEIGHT = 0.6      # 60% weight to ML model
RULES_WEIGHT = 0.4   # 40% weight to rules

# Risk thresholds
RISK_THRESHOLDS = {
    "low": 30,       # Score < 30: Low Risk
    "medium": 60,    # 30 ≤ Score < 60: Medium Risk
    "high": 100      # Score ≥ 60: High Risk
}
```

## 💡 Usage Examples

### Example 1: Low-Risk Transaction
**Input:**
- Amount: ₹2,000
- Account age: 365 days
- Past 24h transactions: 2
- 7-day average: ₹2,500
- Night transaction: No
- New device: No
- New city: No

**Output:** Risk Score: 15 (Low Risk)
**Explanation:** Transaction appears legitimate with minimal risk indicators.

### Example 2: High-Risk Transaction
**Input:**
- Amount: ₹25,000
- Account age: 5 days
- Past 24h transactions: 15
- 7-day average: ₹1,000
- Night transaction: Yes
- New device: Yes
- New city: Yes

**Output:** Risk Score: 85 (High Risk)
**Explanation:** Multiple high-risk characteristics detected:
- High velocity (15 transactions in 24h)
- Amount spike (25x higher than baseline)
- New device + high amount
- New location + night transaction
- New account risk

## 🧪 Testing

### Manual Testing
1. Use the **Live Scoring** tab to test individual transactions
2. Try the **What-If Simulator** to see how parameter changes affect scores
3. Upload test CSVs in **Batch Analyzer**

### Sample Test Cases
The application includes synthetic data with realistic fraud patterns for testing all features.

## 📈 Performance

- **Model Accuracy**: ~92% on test set (synthetic data)
- **Scoring Latency**: <50ms per transaction
- **Batch Processing**: ~100 transactions/second
- **Fraud Detection Rate**: 10% in synthetic dataset

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **ML Framework**: scikit-learn (Random Forest)
- **Data Processing**: pandas, numpy
- **Visualization**: matplotlib, seaborn
- **Model Persistence**: joblib

## 📸 Screenshots

### Live Scoring Interface
*Professional transaction input form with real-time risk assessment*

### Risk Score Display
*Clear visual indicators with score breakdown and explanations*

### Batch Analysis
*Upload and score multiple transactions with summary statistics*

### What-If Simulator
*Interactive parameter adjustment with real-time score updates*

### Analytics Dashboard
*Comprehensive risk analytics with charts and insights*

## 🔒 Security Considerations

- No real PII or sensitive data is stored
- Model operates on extracted features only
- All processing happens server-side
- HTTPS recommended for production deployment

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

Built with ❤️ for production-grade fraud detection

## 🙏 Acknowledgments

- Inspired by real-world fintech fraud detection systems
- Built for educational and demonstration purposes
- Synthetic data generated to simulate realistic fraud patterns

---

**Note**: This is a demonstration project. For production use with real financial data, additional security measures, compliance checks, and extensive testing are required.
