from qdrant_client.models import PointStruct
from uuid import uuid4
from .qdrant_setup import get_client
from .config import COLLECTION_NAME
from .embeddings import embed_text, get_sentiment
import pandas as pd

def ingest_news_data(policy_id: str, file_path: str):
    """Ingest news data with sentiment and reliability tracking."""
    client = get_client()
    df = pd.read_csv(file_path)
    points = []
    
    for _, row in df.iterrows():
        year = int(row['year'])
        headline = str(row['headline'])
        summary = str(row.get('summary', row.get('content', '')))
        content = f"{headline}. {summary}"
        
        vector = embed_text(content)
        sentiment = str(row.get('sentiment', get_sentiment(content))).lower()
        
        payload = {
            "policy_id": policy_id,
            "content": content,
            "headline": headline,
            "year": year,
            "modality": "news",
            "sentiment": sentiment,
            "decay_weight": 1.0,
            "news_source": str(row.get('source', 'Public Record')),
            "evidence_type": "media_discourse", # Explicitly labeling for reasoning trace
            # Multimodal/traceable fields (if available)
            "pdf_page": None,
            "audio_timestamp": None,
            "video_frame": None,
            "evidence_uri": row.get("source", None),
            # Agentic outputs (optional)
            "layman_summary": None,
            "advocacy_letter": None,
            # Evaluation metrics (optional)
            "retrieval_score": None,
            "mrr": None,
            "hit_rate_5": None
        }
        
        points.append(PointStruct(id=str(uuid4()), vector=vector, payload=payload))
        
    if points:
        client.upload_points(collection_name=COLLECTION_NAME, points=points)