"""
ChromaDB Setup - Replaces Qdrant for Docker-free deployment.

ChromaDB is a pure Python vector database with persistent storage,
no Docker required. Provides similar functionality to Qdrant.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Migrated from Qdrant Jan 2024 - setup was too painful for hackathon judges
# ChromaDB just works out of the box, worth the API differences

# Configuration
CHROMADB_DIR = os.getenv("CHROMADB_DIR", "./chromadb_data")
COLLECTION_NAME = "policy_data"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension - don't change without re-ingesting!

# Global client instance
_client = None
_collection = None


def get_client() -> chromadb.Client:
    """Get or create ChromaDB client."""
    global _client
    
    if _client is None:
        try:
            # Use new PersistentClient API (non-deprecated)
            _client = chromadb.PersistentClient(path=CHROMADB_DIR)
            logger.info(f"ChromaDB client initialized at {CHROMADB_DIR}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    return _client


def get_collection():
    """Get or create policy_data collection."""
    global _collection
    
    if _collection is None:
        client = get_client()
        
        try:
            # Try to get existing collection
            _collection = client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            )
            logger.info(f"Loaded existing collection: {COLLECTION_NAME}")
        except Exception:
            # Create new collection if doesn't exist
            _collection = client.create_collection(
                name=COLLECTION_NAME,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                ),
                metadata={"description": "Policy documents, budgets, and news"}
            )
            logger.info(f"Created new collection: {COLLECTION_NAME}")
    
    return _collection


def reset_collection():
    """Delete and recreate the collection (for fresh start)."""
    global _collection
    
    client = get_client()
    
    try:
        # Delete existing collection
        client.delete_collection(name=COLLECTION_NAME)
        logger.info(f"Deleted collection: {COLLECTION_NAME}")
    except Exception as e:
        logger.warning(f"Collection deletion failed (may not exist): {e}")
    
    # Create fresh collection
    _collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        ),
        metadata={"description": "Policy documents, budgets, and news"}
    )
    logger.info(f"Created fresh collection: {COLLECTION_NAME}")
    
    return _collection


def add_documents(
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str]
):
    """
    Add documents to ChromaDB collection.
    
    Args:
        documents: List of text documents
        metadatas: List of metadata dicts (policy_id, year, modality, etc.)
        ids: List of unique IDs
    """
    collection = get_collection()
    
    try:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Added {len(documents)} documents to ChromaDB")
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        raise


def query_documents(
    query_text: str,
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Query ChromaDB for similar documents.
    
    Args:
        query_text: Query string
        n_results: Number of results to return
        where: Filter conditions (e.g., {"policy_id": "NREGA"})
    
    Returns:
        Dict with ids, documents, metadatas, distances
    """
    collection = get_collection()
    
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        return results
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise


def update_metadata(
    ids: List[str],
    metadatas: List[Dict[str, Any]]
):
    """
    Update metadata for existing documents.
    
    Args:
        ids: List of document IDs to update
        metadatas: List of new metadata dicts
    """
    collection = get_collection()
    
    try:
        collection.update(
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"Updated metadata for {len(ids)} documents")
    except Exception as e:
        logger.error(f"Metadata update failed: {e}")
        raise


def delete_documents(ids: List[str]):
    """Delete documents by ID."""
    collection = get_collection()
    
    try:
        collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} documents")
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise


def get_collection_info() -> Dict[str, Any]:
    """
    Get collection statistics.
    
    Returns:
        Dict with count, metadata, etc.
    """
    collection = get_collection()
    
    try:
        count = collection.count()
        
        # Get sample to analyze policy breakdown
        sample = collection.get(limit=10000)  # Get all for stats
        
        policy_breakdown = {}
        if sample and sample['metadatas']:
            for metadata in sample['metadatas']:
                policy_id = metadata.get('policy_id', 'UNKNOWN')
                policy_breakdown[policy_id] = policy_breakdown.get(policy_id, 0) + 1
        
        return {
            "total_points": count,
            "collection_name": COLLECTION_NAME,
            "storage_path": CHROMADB_DIR,
            "policy_breakdown": policy_breakdown,
            "vector_dim": EMBEDDING_DIM
        }
    except Exception as e:
        logger.error(f"Failed to get collection info: {e}")
        raise


def get_all_documents(
    where: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    include_embeddings: bool = False
) -> Dict[str, Any]:
    """
    Retrieve all documents (or filtered subset).
    
    Args:
        where: Filter conditions
        limit: Max number of documents
        include_embeddings: If True, include embeddings in result (needed for drift analysis)
    
    Returns:
        Dict with ids, documents, metadatas, and optionally embeddings
    """
    collection = get_collection()
    
    # Build include list
    include_list = ["documents", "metadatas"]
    if include_embeddings:
        include_list.append("embeddings")
    
    try:
        if where:
            # Query with filter
            results = collection.get(
                where=where,
                limit=limit,
                include=include_list
            )
        else:
            # Get all
            results = collection.get(limit=limit, include=include_list)
        
        return results
    except Exception as e:
        logger.error(f"Failed to retrieve documents: {e}")
        raise


# Initialize on import
try:
    os.makedirs(CHROMADB_DIR, exist_ok=True)
    get_client()
    logger.info("ChromaDB initialized successfully")
except Exception as e:
    logger.error(f"ChromaDB initialization failed: {e}")
