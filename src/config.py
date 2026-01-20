import torch

# Embedding models
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EMBEDDING_DIM = 384

# Qdrant configuration  
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "policy_data" 

# Memory decay parameters
DECAY_RATE = 0.85
REINFORCEMENT_RATE = 1.02
TIME_DECAY_MONTHS = 6

# detection thresholds
DRIFT_HIGH = 0.5
DRIFT_MEDIUM = 0.3
DRIFT_LOW = 0.1

# Data
DATA_DIR = "data"
SAMPLE_TEXT = f"{DATA_DIR}/sample_nrega_2005.txt"
SAMPLE_BUDGET = f"{DATA_DIR}/sample_budgets.csv"
SAMPLE_NEWS = f"{DATA_DIR}/sample_news.csv"
