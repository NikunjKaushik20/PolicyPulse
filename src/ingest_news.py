from uuid import uuid4
from .chromadb_setup import add_documents
from .embeddings import embed_text, get_sentiment
import pandas as pd

def ingest_news_data(policy_id: str, file_path: str):
    """Ingest news data with sentiment and reliability tracking."""
    df = pd.read_csv(file_path, comment='#')
    documents = []
    metadatas = []
    ids = []
    
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
        
        sentiment = str(row['sentiment']).lower() if 'sentiment' in df.columns else get_sentiment(content).lower()
        
        metadata = {
            "policy_id": policy_id,
            "headline": headline,
            "year": year,
            "modality": "news",
            "sentiment": sentiment,
            "news_source": str(row.get('source', 'Public Record')),
            "evidence_type": "media_discourse",
            "evidence_uri": row.get("source", None)
        }
        
        documents.append(content)
        metadatas.append(metadata)
        ids.append(str(uuid4()))
        
    if documents:
        add_documents(documents=documents, metadatas=metadatas, ids=ids)