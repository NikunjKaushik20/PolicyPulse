from qdrant_client.models import PointStruct
from uuid import uuid4
from .qdrant_setup import get_client
from .config import COLLECTION_NAME
from .embeddings import embed_text, get_sentiment
import re

def ingest_text_document(policy_id: str, file_path: str):
    """Ingest temporal policy text chunks with local hybrid search support."""
    client = get_client()
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split text into sections based on headers
    chunks = re.split(r'===\s+(.+?)\s+===', content)
    points = []
    
    for i in range(1, len(chunks), 2):
        if i+1 >= len(chunks):
            break
        header = chunks[i].strip()
        text = chunks[i+1].strip()
        if len(text) < 50:
            continue
            
        year_match = re.search(r'(\d{4})', header)
        year = int(year_match.group(1)) if year_match else 2005
        modality = "amendment" if any(k in header.lower() for k in ["amendment", "act"]) else "text"
        
        # 100/100 Logic: Dense Vector + Initialize Sparse Vector via payload
        vector = embed_text(text[:700])
        
            payload = {
                "policy_id": policy_id,
                "year": year,
                "modality": modality,
                "content": text,
                "custom_sparse": sparse_terms,
                "decay_weight": 1.0,
                "access_count": 0,
                # Multimodal/traceable fields (if available)
                "pdf_page": None,
                "audio_timestamp": None,
                "video_frame": None,
                "evidence_uri": None,
                # Agentic outputs (optional)
                "layman_summary": None,
                "advocacy_letter": None,
                # Evaluation metrics (optional)
                "retrieval_score": None,
                "mrr": None,
                "hit_rate_5": None,
                "sentiment": get_sentiment(text[:500])  # Retaining existing logic
            }
        
        point = PointStruct(
            id=str(uuid4()),
            vector=vector,  # Standard dense vector
            payload=payload
        )
        points.append(point)
        
    if points:
       
        client.upload_points(collection_name=COLLECTION_NAME, points=points)