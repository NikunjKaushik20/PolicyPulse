"""
Qdrant vector database initialization and management.

This module handles connection to the Qdrant vector database, collection
creation, and collection information retrieval.
"""

from typing import Dict, Any, Optional, List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PayloadSchemaType, PointStruct
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

# Qdrant connection configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "policy_data"

# Vector embedding configuration
VECTOR_DIMENSION = 384
DISTANCE_METRIC = Distance.COSINE

# Retry configuration for connection resilience
MAX_RETRY_ATTEMPTS = 3
MIN_RETRY_WAIT_SECONDS = 1
MAX_RETRY_WAIT_SECONDS = 8
DEFAULT_CONNECTION_TIMEOUT = 10.0

# Module-level client singleton
_client: Optional[QdrantClient] = None


@retry(stop=stop_after_attempt(MAX_RETRY_ATTEMPTS), 
       wait=wait_exponential(min=MIN_RETRY_WAIT_SECONDS, max=MAX_RETRY_WAIT_SECONDS))
def get_client() -> QdrantClient:
    """
    Get or create a Qdrant client connection.
    
    Uses exponential backoff retry logic for connection resilience.
    
    Returns:
        QdrantClient: Connected Qdrant client instance.
        
    Raises:
        Exception: If connection to Qdrant fails after all retries.
    """
    global _client
    if _client is None:
        logger.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        try:
            _client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                timeout=DEFAULT_CONNECTION_TIMEOUT,
                prefer_grpc=False
            )
            logger.info("Successfully connected to Qdrant")
        except Exception as connection_error:
            logger.error(f"Failed to connect to Qdrant: {connection_error}")
            raise
    return _client


def create_collection_if_not_exists() -> None:
    """
    Create the policy data collection if it doesn't already exist.
    
    Creates indexes on key fields (policy_id, year, modality) for efficient
    filtering during searches.
    
    Raises:
        Exception: If collection creation fails.
    """
    client = get_client()
    try:
        # Check if collection already exists
        existing_collections = [col.name for col in client.get_collections().collections]
        if COLLECTION_NAME in existing_collections:
            logger.info(f"Collection '{COLLECTION_NAME}' already exists")
            return
        # Multimodal, hybrid, and traceable payload schema for local, agentic governance
        PAYLOAD_SCHEMA = {
            # Core metadata
            "policy_id": PayloadSchemaType.KEYWORD,
            "year": PayloadSchemaType.INTEGER,
            "modality": PayloadSchemaType.KEYWORD,  # text, image, audio, video
            "content": PayloadSchemaType.TEXT,
            "headline": PayloadSchemaType.TEXT,
            "sentiment": PayloadSchemaType.KEYWORD,
            "allocation_crores": PayloadSchemaType.FLOAT,
            "expenditure_crores": PayloadSchemaType.FLOAT,
            "access_count": PayloadSchemaType.INTEGER,
            "decay_weight": PayloadSchemaType.FLOAT,
            "age_years": PayloadSchemaType.INTEGER,
            "last_accessed": PayloadSchemaType.KEYWORD,
            "last_decay_update": PayloadSchemaType.KEYWORD,
            "consolidated_from": PayloadSchemaType.KEYWORD,
            "tags": PayloadSchemaType.KEYWORD,
            "source": PayloadSchemaType.KEYWORD,
            # Hybrid search fields
            "custom_sparse": PayloadSchemaType.TEXT,  # For BM42 sparse vectors
            # Session/interaction memory
            "session_id": PayloadSchemaType.KEYWORD,
            "interaction_id": PayloadSchemaType.KEYWORD,
            # Multimodal vector fields
            "text_vector": PayloadSchemaType.FLOAT,   # FastEmbed/CPU
            "image_vector": PayloadSchemaType.FLOAT,  # CLIP
            "audio_vector": PayloadSchemaType.FLOAT,  # CLAP/Wav2Vec2
            "video_vector": PayloadSchemaType.FLOAT,  # VideoCLIP/Keyframes
            "code_vector": PayloadSchemaType.FLOAT,   # For future extensibility
            # Traceable evidence fields
            "pdf_page": PayloadSchemaType.INTEGER,
            "audio_timestamp": PayloadSchemaType.FLOAT,
            "video_frame": PayloadSchemaType.INTEGER,
            "evidence_uri": PayloadSchemaType.KEYWORD,
            # Binary quantization (for scaling)
            "bq_vector": PayloadSchemaType.KEYWORD,  # Store as binary string
            # Agentic loop outputs
            "layman_summary": PayloadSchemaType.TEXT,
            "advocacy_letter": PayloadSchemaType.TEXT,
            # Evaluation metrics (for local eval)
            "retrieval_score": PayloadSchemaType.FLOAT,
            "mrr": PayloadSchemaType.FLOAT,
            "hit_rate_5": PayloadSchemaType.FLOAT
        }
        # Create new collection with advanced payload schema
        logger.info(f"Creating collection: {COLLECTION_NAME}")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIMENSION, distance=DISTANCE_METRIC),
            payload_schema=PAYLOAD_SCHEMA
        )
        logger.info("Collection created successfully with advanced payload schema")
        # Create indexes for efficient querying
        _create_payload_indexes(client, PAYLOAD_SCHEMA)
    except Exception as error:
        logger.error(f"Error creating collection: {error}")
        raise


def _create_payload_indexes(client: QdrantClient, payload_schema: dict) -> None:
    """
    Create payload indexes for all non-TEXT fields in the payload schema.
    Args:
        client: QdrantClient instance to use for index creation.
        payload_schema: dict of field_name to PayloadSchemaType
    Note:
        Silently continues if indexes already exist.
    """
    for field_name, schema_type in payload_schema.items():
        if schema_type != PayloadSchemaType.TEXT:
            try:
                client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=schema_type
                )
                logger.info(f"Created index on field: {field_name}")
            except Exception as error:
                logger.warning(f"Could not create index on {field_name}: {error}")


def get_collection_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the policy data collection.
    
    Returns:
        Dict containing:
            - collection_name: Name of the collection
            - total_points: Total number of vectors in collection
            - vector_dim: Dimension of vectors
            - distance: Distance metric (COSINE)
            - policy_breakdown: Count of vectors per policy
            - status: Overall health status
            
    Raises:
        Exception: If unable to retrieve collection information.
    """
    client = get_client()
    
    try:
        # List of all supported policies
        supported_policies = [
            "NREGA", "RTI", "NEP", "PM-KISAN", "SWACHH-BHARAT",
            "DIGITAL-INDIA", "AYUSHMAN-BHARAT", "MAKE-IN-INDIA",
            "SKILL-INDIA", "SMART-CITIES"
        ]
        
        # Retrieve all points and count by policy
        all_points = _retrieve_all_collection_points(client)
        
        # Aggregate counts by policy_id
        policy_counts = {}
        for point in all_points:
            policy_id = point.payload.get("policy_id")
            if policy_id:
                policy_counts[policy_id] = policy_counts.get(policy_id, 0) + 1
        
        # Ensure all policies are in breakdown (even if empty)
        policy_breakdown = {policy: policy_counts.get(policy, 0) for policy in supported_policies}
        
        total_count = len(all_points)
        
        return {
            "collection_name": COLLECTION_NAME,
            "total_points": total_count,
            "vector_dim": VECTOR_DIMENSION,
            "distance": "COSINE",
            "policy_breakdown": policy_breakdown,
            "status": "healthy"
        }
        
    except Exception as error:
        logger.error(f"Failed to get collection statistics: {error}")
        raise


def _retrieve_all_collection_points(client: QdrantClient, batch_size: int = 100) -> List:
    """
    Retrieve all points from the collection with pagination.
    
    Args:
        client: QdrantClient instance.
        batch_size: Number of points to retrieve per request.
        
    Returns:
        List of all PointStruct objects in the collection.
    """
    all_points = []
    offset = None
    
    while True:
        batch_points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        all_points.extend(batch_points)
        
        if next_offset is None:
            break
        offset = next_offset
    
    return all_points
