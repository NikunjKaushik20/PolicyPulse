"""
Policy recommendation and cross-policy analysis module.

Provides functions to:
- Find related policies based on semantic similarity
- Query temporal distribution of policy data
- Generate cross-policy insights for comparative analysis
"""

from typing import List, Dict, Optional, Any
import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Recommendation defaults
DEFAULT_RECOMMENDATIONS_COUNT = 5
DEFAULT_CROSS_POLICY_COUNT = 3
DEFAULT_CHUNKS_PER_POLICY = 2

# Search multiplier for deduplication
SEARCH_OVERSAMPLING_FACTOR = 3

# Content preview length
SAMPLE_TEXT_LENGTH = 200

# Collection name for ChromaDB
COLLECTION_NAME = "policy_documents"
PERSIST_DIRECTORY = "chromadb_data"

_client_instance = None
_collection_instance = None

def get_collection():
    """Get or create cached ChromaDB collection."""
    global _client_instance, _collection_instance
    if _collection_instance is None:
        if _client_instance is None:
            _client_instance = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
        
        # Use default embedding function (all-MiniLM-L6-v2) or specify one
        ef = embedding_functions.DefaultEmbeddingFunction()
        _collection_instance = _client_instance.get_or_create_collection(
            name=COLLECTION_NAME, 
            embedding_function=ef
        )
    return _collection_instance


def get_related_policies(
    policy_id: str,
    year: Optional[int] = None,
    top_k: int = DEFAULT_RECOMMENDATIONS_COUNT
) -> List[Dict[str, Any]]:
    """
    Find policies related to the given policy based on semantic similarity.
    """
    collection = get_collection()
    
    # Fail-safe if collection empty
    if collection.count() == 0:
        logger.warning("No documents in collection.")
        return []

    # Get sample document from source policy
    where_filter = {"policy_id": policy_id}
    if year:
        where_filter["year"] = int(year)  # Chroma assumes standard types

    results = collection.get(
        where=where_filter,
        limit=1,
        include=["embeddings"]
    )
    
    if not results['embeddings']:
        logger.warning(f"No sample found for policy {policy_id}")
        return []
    
    sample_embedding = results['embeddings'][0]
    
    # Query for similar documents from OTHER policies
    # Chroma where clause: policy_id != source_policy_id
    search_results = collection.query(
        query_embeddings=[sample_embedding],
        n_results=top_k * SEARCH_OVERSAMPLING_FACTOR,
        where={"policy_id": {"$ne": policy_id}}
    )
    
    # Process results
    related_by_policy = {}
    
    if not search_results['metadatas'] or not search_results['metadatas'][0]:
        return []

    metadatas = search_results['metadatas'][0]
    documents = search_results['documents'][0]
    distances = search_results['distances'][0]  # Smaller is better for L2, cosine dist
    
    for i, metadata in enumerate(metadatas):
        related_policy_id = metadata.get("policy_id")
        
        if related_policy_id not in related_by_policy:
            # Simple similarity score conversion (assuming distance is cosine distance ~0..2)
            # Actually Chroma default is L2. For simplified UX, let's just use 1/(1+dist)
            dist = distances[i]
            score = 1 / (1 + dist)
            
            related_by_policy[related_policy_id] = {
                "policy_id": related_policy_id,
                "year": metadata.get("year"),
                "similarity_score": score,
                "sample_text": (documents[i] or "")[:SAMPLE_TEXT_LENGTH] + "..."
            }
        
        if len(related_by_policy) >= top_k:
            break
            
    logger.info(f"Found {len(related_by_policy)} related policies for {policy_id}")
    return list(related_by_policy.values())


def get_policy_by_year_range(
    policy_id: str,
    start_year: int,
    end_year: int
) -> Dict[int, int]:
    """
    Get count of data points for a policy across a year range.
    """
    collection = get_collection()
    year_distribution = {}
    
    # Chroma doesn't have aggregate counts easily, so we iterate (inefficient but works for small data)
    # Alternatively we just query for the policy_id and aggregate in python
    
    results = collection.get(
        where={"policy_id": policy_id},
        include=["metadatas"]
    )
    
    for meta in results['metadatas']:
        y_str = meta.get("year")
        try:
            y = int(y_str)
            if start_year <= y <= end_year:
                year_distribution[y] = year_distribution.get(y, 0) + 1
        except:
            pass
            
    logger.info(f"Year distribution for {policy_id}: {year_distribution}")
    return year_distribution


def get_cross_policy_insights(
    query_text: str,
    top_policies: int = DEFAULT_CROSS_POLICY_COUNT,
    chunks_per_policy: int = DEFAULT_CHUNKS_PER_POLICY
) -> List[Dict[str, Any]]:
    """
    Find insights across multiple policies for a given query.
    """
    collection = get_collection()
    
    search_results = collection.query(
        query_texts=[query_text],
        n_results=top_policies * chunks_per_policy * SEARCH_OVERSAMPLING_FACTOR
    )
    
    if not search_results['metadatas'] or not search_results['metadatas'][0]:
        return []

    metadatas = search_results['metadatas'][0]
    documents = search_results['documents'][0]
    distances = search_results['distances'][0]
    
    policy_groups = {}
    
    for i, meta in enumerate(metadatas):
        policy_id = meta.get("policy_id")
        
        if policy_id not in policy_groups:
            policy_groups[policy_id] = {
                "policy_id": policy_id,
                "chunks": []
            }
            
        if len(policy_groups[policy_id]["chunks"]) < chunks_per_policy:
            dist = distances[i]
            score = 1 / (1 + dist)
            
            policy_groups[policy_id]["chunks"].append({
                "text": documents[i],
                "year": meta.get("year"),
                "score": score
            })
            
        # Check breakout condition
        if len(policy_groups) >= top_policies:
            if all(len(g["chunks"]) >= chunks_per_policy for g in policy_groups.values()):
                break

    return list(policy_groups.values())
