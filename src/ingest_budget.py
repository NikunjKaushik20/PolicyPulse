from qdrant_client.models import PointStruct
from uuid import uuid4
from .qdrant_setup import get_client
from .config import COLLECTION_NAME
from .embeddings import embed_text
import pandas as pd

def ingest_budget_data(policy_id: str, file_path: str):
    """Ingest budget data with enhanced metadata for societal impact tracking."""
    client = get_client()
    df = pd.read_csv(file_path)
    points = []
    
    for _, row in df.iterrows():
        year = int(row['year'])
        allocation = float(row.get('allocated_crores', row.get('allocation', 0)))
        expenditure = float(row.get('spent_crores', row.get('expenditure', 0)))
        
        content = f"Budget for {policy_id} year {year}: allocated {allocation}Cr, spent {expenditure}Cr"
        extra_fields = {}
        
        # Advanced Field Mapping for Specific Impact Metrics
        metric_map = {
            'focus_area': 'focus',
            'person_days_million': 'person_days',
            'beneficiaries_million': 'beneficiaries',
            'toilets_built_million': 'toilets',
            'digital_transactions_billion': 'transactions'
        }
        
        for col, key in metric_map.items():
            if col in df.columns and pd.notna(row.get(col)):
                val = row[col]
                content += f". {key.replace('_', ' ').title()}: {val}"
                extra_fields[key] = val

        vector = embed_text(content)
        payload = {
            "policy_id": policy_id,
            "year": year,
            "modality": "budget",
            "content": content,
            "allocation_crores": allocation,
            "expenditure_crores": expenditure,
            "utilization_rate": round((expenditure / allocation) * 100, 2) if allocation > 0 else 0,
            "decay_weight": 1.0,
            "access_count": 0,
            "custom_sparse": None,
            "source": file_path,
            # Multimodal/traceable fields (if available)
            "pdf_page": None,
            "audio_timestamp": None,
            "video_frame": None,
            "evidence_uri": file_path,
            # Agentic outputs (optional)
            "layman_summary": None,
            "advocacy_letter": None,
            # Evaluation metrics (optional)
            "retrieval_score": None,
            "mrr": None,
            "hit_rate_5": None
        }
        payload.update(extra_fields)
        
        points.append(PointStruct(id=str(uuid4()), vector=vector, payload=payload))
        
    if points:
        client.upload_points(collection_name=COLLECTION_NAME, points=points)