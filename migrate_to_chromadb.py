"""
Migration script: Qdrant → ChromaDB

This script exports data from Qdrant (if running) and imports into ChromaDB.
If Qdrant is not running, skip directly to fresh ingestion.
"""

import os
import sys
import logging
from typing import List, Dict, Any
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_from_qdrant():
    """Attempt to export data from Qdrant if available."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Filter
        
        # Try to connect to Qdrant
        qdrant_client = QdrantClient(host="localhost", port=6333, timeout=5)
        
        # Check if collection exists
        try:
            collection_info = qdrant_client.get_collection("policy_data")
            logger.info(f"Found Qdrant collection with {collection_info.points_count} points")
        except Exception:
            logger.warning("Qdrant collection not found. Will start fresh.")
            return None
        
        # Export all points
        logger.info("Exporting data from Qdrant...")
        points, _ = qdrant_client.scroll(
            collection_name="policy_data",
            limit=100000,  # Get all
            with_payload=True,
            with_vectors=False  # Don't need vectors, will re-embed
        )
        
        # Transform to ChromaDB format
        documents = []
        metadatas = []
        ids = []
        
        for point in points:
            payload = point.payload
            
            # Extract content
            content = payload.get("content", "")
            if not content:
                continue
            
            # Build metadata (exclude content from metadata)
            metadata = {
                "policy_id": payload.get("policy_id", "UNKNOWN"),
                "year": str(payload.get("year", "2020")),
                "modality": payload.get("modality", "temporal"),
                "sentiment": payload.get("sentiment", "neutral"),
                "decay_weight": payload.get("decay_weight", 1.0),
                "access_count": payload.get("access_count", 0),
            }
            
            # Add optional fields if present
            if "headline" in payload:
                metadata["headline"] = payload["headline"]
            if "source" in payload:
                metadata["source"] = payload["source"]
            
            documents.append(content)
            metadatas.append(metadata)
            ids.append(str(uuid4()))
        
        logger.info(f"Exported {len(documents)} documents from Qdrant")
        return {
            "documents": documents,
            "metadatas": metadatas,
            "ids": ids
        }
        
    except ImportError:
        logger.info("Qdrant client not installed. Skipping migration.")
        return None
    except Exception as e:
        logger.warning(f"Could not connect to Qdrant: {e}. Will start fresh.")
        return None


def import_to_chromadb(data: Dict[str, List]):
    """Import data into ChromaDB."""
    from src.chromadb_setup import add_documents, reset_collection
    
    logger.info("Resetting ChromaDB collection...")
    reset_collection()
    
    if data and data["documents"]:
        logger.info(f"Importing {len(data['documents'])} documents to ChromaDB...")
        
        # ChromaDB has a batch limit, so chunk imports
        BATCH_SIZE = 100
        documents = data["documents"]
        metadatas = data["metadatas"]
        ids = data["ids"]
        
        for i in range(0, len(documents), BATCH_SIZE):
            batch_docs = documents[i:i+BATCH_SIZE]
            batch_meta = metadatas[i:i+BATCH_SIZE]
            batch_ids = ids[i:i+BATCH_SIZE]
            
            add_documents(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
            logger.info(f"Imported batch {i//BATCH_SIZE + 1}/{(len(documents)-1)//BATCH_SIZE + 1}")
        
        logger.info("✅ Migration complete!")
    else:
        logger.info("No data to import. Run 'python cli.py ingest-all' to populate.")


if __name__ == "__main__":
    logger.info("Starting Qdrant → ChromaDB migration...")
    
    # Step 1: Try to export from Qdrant
    exported_data = migrate_from_qdrant()
    
    # Step 2: Import to ChromaDB (or create empty collection)
    import_to_chromadb(exported_data)
    
    logger.info("Migration script finished!")
    logger.info("Next steps:")
    logger.info("  1. If no data was migrated, run: python cli.py ingest-all")
    logger.info("  2. Start the server: python start.py")
