from qdrant_client.models import PointStruct
from uuid import uuid4
from .qdrant_setup import get_client
from .config import COLLECTION_NAME
from .embeddings import embed_text, get_sentiment
import pandas as pd

def ingest_news_data(policy_id: str, file_path: str):
    """Ingest news data with sentiment and reliability tracking."""
    client = get_client()
    df = pd.read_csv(file_path, comment='#')
    points = []
    
    for _, row in df.iterrows():
        year = int(row['year'])
        headline = str(row['headline'])
        # Handle different column names for summary
        summary = ''
        if 'summary' in df.columns:
            summary = str(row['summary'])
        elif 'content' in df.columns:
            summary = str(row['content'])
        elif 'impact_score' in df.columns:
            summary = f"Impact score: {row['impact_score']}"
        
        content = f"{headline}. {summary}" if summary else headline
        
        vector = embed_text(content)
        sentiment = str(row['sentiment']).lower() if 'sentiment' in df.columns else get_sentiment(content).lower()
        
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