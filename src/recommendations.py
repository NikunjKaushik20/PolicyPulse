"""
Policy recommendation and cross-policy analysis module.

Provides functions to:
- Find related policies based on semantic similarity
- Query temporal distribution of policy data
- Generate cross-policy insights for comparative analysis
"""

from typing import List, Dict, Optional, Any
import logging
from .qdrant_setup import get_client, COLLECTION_NAME
from .embeddings import embed_text
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

# Recommendation defaults
DEFAULT_RECOMMENDATIONS_COUNT = 5
DEFAULT_CROSS_POLICY_COUNT = 3
DEFAULT_CHUNKS_PER_POLICY = 2

# Search multiplier for deduplication
SEARCH_OVERSAMPLING_FACTOR = 3

# Content preview length
SAMPLE_TEXT_LENGTH = 200


def get_related_policies(
    policy_id: str,
    year: Optional[int] = None,
    top_k: int = DEFAULT_RECOMMENDATIONS_COUNT
) -> List[Dict[str, Any]]:
    """
    Find policies related to the given policy based on semantic similarity.
    
    Finds a representative sample from the specified policy and searches
    for similar content across other policies. Returns the best match
    from each related policy.
    
    Args:
        policy_id: Source policy to find relatives for.
        year: Optional year filter to find samples from.
        top_k: Maximum number of related policies to return.
        
    Returns:
        List[Dict] of related policies with similarity scores:
            - policy_id: Related policy name
            - year: Year of the match
            - similarity_score: Cosine similarity (0-1)
            - sample_text: Preview of the matching content
            
    Raises:
        Exception: If search fails.
    """
    client = get_client()
    
    # Build filter for source policy
    source_filter_conditions = [
        FieldCondition(key="policy_id", match=MatchValue(value=policy_id))
    ]
    
    if year:
        source_filter_conditions.append(
            FieldCondition(key="year", match=MatchValue(value=str(year)))
        )
    
    # Retrieve sample point from source policy
    sample_points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(must=source_filter_conditions),
        limit=1,
        with_vectors=True
    )
    
    if not sample_points:
        logger.warning(f"No sample found for policy {policy_id}")
        return []
    
    sample_vector = sample_points[0].vector
    
    # Search across other policies for similar content
    search_results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=sample_vector,
        query_filter=Filter(
            must_not=[
                FieldCondition(key="policy_id", match=MatchValue(value=policy_id))
            ]
        ),
        limit=top_k * SEARCH_OVERSAMPLING_FACTOR  # Over-fetch for deduplication
    )
    
    # Keep only the best match per policy (deduplication)
    related_by_policy = {}
    for result in search_results:
        related_policy_id = result.payload.get("policy_id")
        if related_policy_id not in related_by_policy:
            related_by_policy[related_policy_id] = {
                "policy_id": related_policy_id,
                "year": result.payload.get("year"),
                "similarity_score": result.score,
                "sample_text": result.payload.get("content", "")[:SAMPLE_TEXT_LENGTH] + "..."
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
    
    Useful for understanding data coverage and temporal distribution.
    
    Args:
        policy_id: Policy to analyze.
        start_year: Inclusive start year.
        end_year: Inclusive end year.
        
    Returns:
        Dict mapping year -> count of data points.
        Only years with at least 1 point are included.
        
    Raises:
        Exception: If count query fails.
    """
    client = get_client()
    year_distribution = {}
    
    for year in range(start_year, end_year + 1):
        # Count points matching policy and year
        count_result = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[
                    FieldCondition(key="policy_id", match=MatchValue(value=policy_id)),
                    FieldCondition(key="year", match=MatchValue(value=str(year)))
                ]
            )
        )
        
        if count_result.count > 0:
            year_distribution[year] = count_result.count
    
    logger.info(f"Year distribution for {policy_id}: {year_distribution}")
    return year_distribution


def get_cross_policy_insights(
    query_text: str,
    top_policies: int = DEFAULT_CROSS_POLICY_COUNT,
    chunks_per_policy: int = DEFAULT_CHUNKS_PER_POLICY
) -> List[Dict[str, Any]]:
    """
    Find insights across multiple policies for a given query.
    
    Performs a single semantic search and groups results by policy,
    returning the most relevant chunks from each policy. Useful for
    comparative policy analysis.
    
    Args:
        query_text: Query text to search for across policies.
        top_policies: Number of policies to include.
        chunks_per_policy: Number of result chunks per policy.
        
    Returns:
        List[Dict] of policy groups with chunks:
            - policy_id: Policy name
            - chunks: List of matching content chunks with scores
            
    Raises:
        Exception: If search fails.
    """
    client = get_client()
    
    # Embed query and search across all policies
    query_vector = embed_text(query_text)
    
    search_results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_policies * chunks_per_policy * SEARCH_OVERSAMPLING_FACTOR
    )
    
    # Group results by policy
    policy_groups = {}
    for result in search_results:
        policy_id = result.payload.get("policy_id")
        
        # Initialize policy group if new
        if policy_id not in policy_groups:
            policy_groups[policy_id] = {
                "policy_id": policy_id,
                "chunks": []
            }
        
        # Add chunk if we haven't reached the limit for this policy
        if len(policy_groups[policy_id]["chunks"]) < chunks_per_policy:
            policy_groups[policy_id]["chunks"].append({
                "text": result.payload.get("content"),
                "year": result.payload.get("year"),
                "score": result.score
            })
        
        # Early exit if we have enough policies with enough chunks
        if len(policy_groups) >= top_policies:
            if all(
                len(group["chunks"]) >= chunks_per_policy
                for group in policy_groups.values()
            ):
                break
    
    logger.info(
        f"Cross-policy insights: {len(policy_groups)} policies, "
        f"{sum(len(g['chunks']) for g in policy_groups.values())} chunks"
    )
    return list(policy_groups.values())
