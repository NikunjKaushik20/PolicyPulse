"""
Memory management for policy data with time decay and reinforcement.

This module implements adaptive memory mechanisms:
- Time decay: older data naturally decreases in relevance
- Access reinforcement: frequently accessed data becomes more relevant
- Memory consolidation: similar memories are merged to reduce redundancy
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from .qdrant_setup import get_client, COLLECTION_NAME
from qdrant_client.models import Filter, FieldCondition, MatchValue
import math
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Memory decay configuration
DECAY_COEFFICIENT = 0.1  # Exponential decay rate per year
ACCESS_BOOST_RATE = 0.02  # Boost per access (2% per hit)
MAX_BOOST_MULTIPLIER = 1.3  # Cap on cumulative access boost
MAX_DECAY_WEIGHT = 1.5  # Absolute maximum decay weight value
DEFAULT_DECAY_WEIGHT = 1.0  # Initial weight for new entries

# Batch processing configuration
BATCH_SIZE = 100

# Consolidation defaults
DEFAULT_SIMILARITY_THRESHOLD = 0.95


def reinforce_memory_batch(point_ids: List[str]) -> None:
    """
    Increase relevance weight of accessed data points.
    
    Implements the reinforcement mechanism where accessing data increases
    its weight through both access counting and decay weight boost.
    
    Args:
        point_ids: List of point IDs to reinforce.
        
    Returns:
        None
        
    Note:
        Silently ignores empty lists. Logs errors but continues on individual failures.
    """
    if not point_ids:
        return
    
    client = get_client()
    try:
        points = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=point_ids,
            with_payload=True,
            with_vectors=False
        )
        if not points:
            return
        for point in points:
            # Update access counter
            current_access_count = point.payload.get('access_count', 0)
            point.payload['access_count'] = current_access_count + 1
            point.payload['last_accessed'] = datetime.now().isoformat()
            # Apply access-based boost with diminishing returns
            current_decay_weight = point.payload.get('decay_weight', DEFAULT_DECAY_WEIGHT)
            access_boost = min(
                ACCESS_BOOST_RATE * point.payload['access_count'],
                MAX_BOOST_MULTIPLIER
            )
            point.payload['decay_weight'] = min(
                current_decay_weight * (1 + access_boost),
                MAX_DECAY_WEIGHT
            )
            # Persist updates
            client.set_payload(
                collection_name=COLLECTION_NAME,
                payload=point.payload,
                points=[point.id]
            )
    except Exception as error:
        logger.error(f"Failed to reinforce memory batch: {error}")


def apply_time_decay(
    policy_id: Optional[str] = None,
    current_year: int = 2026
) -> int:
    """
    Apply exponential decay to all points based on age.
    
    Newer data (closer to current_year) maintains higher relevance weights,
    while older data naturally decays according to exp(-coefficient * age).
    
    Args:
        policy_id: Optional filter to apply decay only to this policy.
        current_year: Reference year for age calculation (default 2026).
        
    Returns:
        int: Number of points updated.
        
    Raises:
        Exception: If database operations fail.
    """
    client = get_client()
    
    # Build filter condition if policy is specified
    filters = []
    if policy_id:
        filters.append(FieldCondition(key="policy_id", match=MatchValue(value=policy_id)))
    
    scroll_filter = Filter(must=filters) if filters else None
    
    while True:
        batch_points, next_offset = client.scroll(

      

            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        if not batch_points:
            break
        
        for point in batch_points:
            year = point.payload.get("year")
            if year:
                try:
                    year_int = int(year)
                    age_years = current_year - year_int
                    # Exponential decay: weight decreases with age
                    decay_weight = math.exp(-DECAY_COEFFICIENT * age_years)
                    
                    client.set_payload(
                        collection_name=COLLECTION_NAME,
                        payload={
                            "decay_weight": decay_weight,
                            "age_years": age_years,
                            "last_decay_update": datetime.now().isoformat()
                        },
                        points=[point.id]
                    )
                    updated_count += 1
                    
                except ValueError:
                    logger.warning(f"Invalid year format: {year}")
                    continue
        
        if next_offset is None:
            break
        offset = next_offset
    
    logger.info(f"Applied time decay to {updated_count} points")
    return updated_count


def get_memory_health(policy_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze memory statistics for health monitoring.
    
    Returns aggregate metrics about access patterns and decay distribution,
    useful for system health monitoring and optimization.
    
    Args:
        policy_id: Optional filter to analyze only this policy.
        
    Returns:
        Dict containing:
            - total_points: Count of data points
            - total_accesses: Sum of all access counts
            - avg_access_per_point: Mean accesses per point
            - avg_decay_weight: Mean decay weight
            - min/max_decay_weight: Range of decay weights
            - age_distribution: Histogram of point ages
            
    Raises:
        Exception: If database query fails.
    """
    client = get_client()
    
    filters = []
    if policy_id:
        filters.append(FieldCondition(key="policy_id", match=MatchValue(value=policy_id)))
    
    scroll_filter = Filter(must=filters) if filters else None
    
    total_points = 0

        

    total_accesses = 0
    decay_weights = []
    age_distribution = {}
    offset = None
    
    while True:
        batch_points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        if not batch_points:
            break
        
        for point in batch_points:
            total_points += 1
            total_accesses += point.payload.get("access_count", 0)
            decay_weights.append(point.payload.get("decay_weight", DEFAULT_DECAY_WEIGHT))
            
            age = point.payload.get("age_years", 0)
            age_distribution[age] = age_distribution.get(age, 0) + 1
        
        if next_offset is None:
            break
        offset = next_offset
    
    if total_points == 0:
        return {
            "error": "No points found for specified policy",
            "policy_id": policy_id
        }
    
    return {
        "total_points": total_points,
        "total_accesses": total_accesses,
        "avg_access_per_point": round(total_accesses / total_points, 2),
        "avg_decay_weight": round(float(np.mean(decay_weights)), 3),
        "min_decay_weight": round(float(np.min(decay_weights)), 3),
        "max_decay_weight": round(float(np.max(decay_weights)), 3),
        "age_distribution": age_distribution
    }


def consolidate_memories(
    policy_id: str,
    year: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
) -> int:
    """
    Merge similar memories to reduce redundancy.
    
    Identifies similar points (by cosine similarity) and merges them,
    preserving access counts and consolidation history.
    
    Args:
        policy_id: Policy to consolidate.
        year: Year to consolidate.
        similarity_threshold: Cosine similarity threshold (0-1) for merging.
        
    Returns:
        int: Number of duplicates consolidated.
        
    Raises:
        Exception: If database operations fail.
    """
    client = get_client()
    
    # Retrieve all points for this policy-year combination
    filters = [
        FieldCondition(key="policy_id", match=MatchValue(value=policy_id)),
        FieldCondition(key="year", match=MatchValue(value=year))
    ]
    
    points_batch, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(must=filters),
        limit=1000,
        with_vectors=True,
        with_payload=True
    )
    
    if len(points_batch) < 2:
        logger.info(f"Insufficient points to consolidate: {len(points_batch)}")
        return 0
    
    consolidated_count = 0
    points_to_delete = []
    processed_point_ids = set()
    
    # Compare each pair of points
    for i in range(len(points_batch)):
        if points_batch[i].id in points_to_delete or points_batch[i].id in processed_point_ids:
            continue
        
        for j in range(i + 1, len(points_batch)):
            if points_batch[j].id in points_to_delete or points_batch[j].id in processed_point_ids:
                continue
            
            # Calculate cosine similarity
            vector_i = np.array(points_batch[i].vector)
            vector_j = np.array(points_batch[j].vector)
            similarity = np.dot(vector_i, vector_j) / (

       

                np.linalg.norm(vector_i) * np.linalg.norm(vector_j)
            )
            
            if similarity >= similarity_threshold:
                # Merge the two points, keeping the one with more accesses
                access_count_i = points_batch[i].payload.get("access_count", 0)
                access_count_j = points_batch[j].payload.get("access_count", 0)
                
                if access_count_i >= access_count_j:
                    # Keep point i, delete point j
                    points_batch[i].payload['access_count'] = access_count_i + access_count_j
                    consolidated_from = points_batch[i].payload.get("consolidated_from", [])
                    consolidated_from.append(str(points_batch[j].id))
                    points_batch[i].payload['consolidated_from'] = consolidated_from
                    
                    client.set_payload(
                        collection_name=COLLECTION_NAME,
                        payload=points_batch[i].payload,
                        points=[points_batch[i].id]
                    )
                    points_to_delete.append(points_batch[j].id)
                    processed_point_ids.add(points_batch[i].id)
                else:
                    # Keep point j, delete point i
                    points_batch[j].payload['access_count'] = access_count_i + access_count_j
                    consolidated_from = points_batch[j].payload.get("consolidated_from", [])
                    consolidated_from.append(str(points_batch[i].id))
                    points_batch[j].payload['consolidated_from'] = consolidated_from
                    
                    client.set_payload(
                        collection_name=COLLECTION_NAME,
                        payload=points_batch[j].payload,
                        points=[points_batch[j].id]
                    )
                    points_to_delete.append(points_batch[i].id)
                    processed_point_ids.add(points_batch[j].id)
                
                consolidated_count += 1
                break
    
    # Delete duplicate points
    if points_to_delete:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=points_to_delete
        )
        logger.info(f"Consolidated {consolidated_count} duplicate memories")
    
    return consolidated_count
