from uuid import uuid4
from .chromadb_setup import add_documents
from .embeddings import embed_text, get_sentiment
import re

def ingest_text_document(policy_id: str, file_path: str):
    """Ingest temporal policy text chunks with local hybrid search support."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split text into sections based on headers
    chunks = re.split(r'===\s+(.+?)\s+===', content)
    documents = []
    metadatas = []
    ids = []
    
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
        
        metadata = {
            "policy_id": policy_id,
            "year": year,
            "modality": modality,
            "sentiment": get_sentiment(text[:500])
        }
        
        documents.append(text)
        metadatas.append(metadata)
        ids.append(str(uuid4()))
        
    if documents:
        add_documents(documents=documents, metadatas=metadatas, ids=ids)