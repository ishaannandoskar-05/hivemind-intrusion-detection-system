# Hivemind Intrusion Detection System

A real-time Host-based Intrusion Detection System (HIDS) that uses an ensemble of three ML models with strict majority voting to classify network traffic as Normal or Attack, achieving 99.38% accuracy and 0.97 ROC-AUC on 1.9M network flows from the CIC-IDS 2017 dataset.

## Architecture
```bash
Live Traffic (Scapy)
↓
Kafka: raw_flows
↓
Hivemind Detector (RF + SGD + Extra Trees)
↓
Kafka: predictions
↓
Alert Agent → MongoDB Atlas
↓
React Dashboard (Flask API)
```
## Features

- **Hivemind Voting** — all 3 models must agree to flag an Attack, reducing false positives by 95.5%
- **Live Packet Capture** — Scapy sniffs network traffic and publishes flows to Kafka in real time
- **Persistent Storage** — MongoDB Atlas stores alerts and normal flows per browser session
- **React Dashboard** — live alert feed, blacklist tracker, Kafka monitor, log viewer, and model performance metrics
- **Binary Classification** — Normal vs Attack on 1.9M samples with severe class imbalance handled via SMOTE and dynamic class weights

## Model Performance

| Metric    | Score  |
|-----------|--------|
| Accuracy  | 99.38% |
| F1 Score  | 97.36% |
| ROC-AUC   | 97.73% |
| Precision | 99.00% |
| Recall    | 96.00% |

| Confusion Matrix     | Count   |
|----------------------|---------|
| True Negatives       | 339,306 |
| False Positives      | 343     |
| False Negatives      | 2,060   |
| True Positives       | 44,337  |

## Tech Stack

- **ML** — Scikit-learn (Random Forest, Extra Trees, SGDClassifier), imbalanced-learn (SMOTE)
- **Streaming** — Apache Kafka, kafka-python
- **Capture** — Scapy
- **Backend** — Flask, Flask-CORS, PyMongo
- **Frontend** — React, Recharts, Lucide
- **Database** — MongoDB Atlas
- **Infrastructure** — Docker, python-dotenv

## Dataset

CIC-IDS 2017 (Canadian Institute for Cybersecurity)
- 1,930,227 total samples
- 8 classes collapsed to binary (Normal / Attack)
- Training: 1,544,181 samples | Testing: 386,046 samples

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker Desktop
- MongoDB Atlas account (free tier)

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/hivemind-intrusion-detection-system.git
cd hivemind-intrusion-detection-system

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB Atlas URL and Kafka settings
```

### Run

```bash
# Start Kafka
docker compose up -d

# Train models (first time only)
python train.py

# Terminal 1 — Live detection pipeline
python live_main.py

# Terminal 2 — Flask API
python server.py

# Terminal 3 — React frontend
cd frontend && npm start
```

Open **http://localhost:3000**

## Project Structure
```bash
hivemind-intrusion-detection-system/
├── agents/
│   ├── traffic_collector.py        # Dataset loading and feature engineering
│   ├── preprocessing_agent.py      # Scaling, SMOTE, class weights
│   ├── detection_agent.py          # Hivemind ensemble training and evaluation
│   ├── live_traffic_collector.py   # Scapy packet capture → Kafka
│   ├── live_detector.py            # Kafka consumer → ML prediction → Kafka
│   ├── alert_agent.py              # Kafka consumer → alerts → MongoDB
│   └── attack_intelligence_agent.py # IP threat scoring and blacklisting
├── frontend/                       # React dashboard
├── models/                         # Trained .pkl files (not committed)
├── logs/                           # alerts.log
├── server.py                       # Flask API + MongoDB
├── train.py                        # Training pipeline
├── live_main.py                    # Launches all agents in parallel
├── docker-compose.yml              # Kafka setup
└── .env.example                    # Environment variable template
```
## License

MIT