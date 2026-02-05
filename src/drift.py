
from typing import List, Dict, Optional, Any
import numpy as np
import logging
from .qdrant_setup import get_client, COLLECTION_NAME
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

# These thresholds were calibrated against NREGA 2008-2023 data
# may need adjustment for policies with less historical coverage

DRIFT_CRITICAL_THRESHOLD = 0.70
DRIFT_HIGH_THRESHOLD = 0.45
DRIFT_MEDIUM_THRESHOLD = 0.25
DRIFT_LOW_THRESHOLD = 0.10

DRIFT_SEVERITY_LEVELS = {
    "CRITICAL": DRIFT_CRITICAL_THRESHOLD,
    "HIGH": DRIFT_HIGH_THRESHOLD,
    "MEDIUM": DRIFT_MEDIUM_THRESHOLD,
    "LOW": DRIFT_LOW_THRESHOLD,
    "MINIMAL": 0.0
}

MIN_SAMPLES_PER_YEAR = 1  # bumped down from 3, some years have sparse data
MIN_YEARS_FOR_TIMELINE = 2

VECTOR_SIMILARITY_BOUNDS = (-1.0, 1.0)


def compute_drift_timeline(
    policy_id: str,
    modality: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Compute semantic drift across years for a policy.
    
    Analyzes policy evolution by:
    1. Retrieving all embeddings for each year
    2. Computing year-centroid vectors
    3. Measuring cosine similarity between consecutive years
    4. Converting similarity to drift scores
    5. Classifying severity
    
    Args:
        policy_id: Policy to analyze.
        modality: Optional filter (budget/news/temporal).
        
    Returns:
        List[Dict] with timeline of drift scores, or None if insufficient data:
            - from_year, to_year: Year range
            - drift_score: 0-1 (higher = more change)
            - severity: CRITICAL/HIGH/MEDIUM/LOW/MINIMAL
            - samples_year1, samples_year2: Data point counts
            - similarity: Cosine similarity of year centroids
            
    Raises:
        Exception: If database query fails.
    """
    client = get_client()
    
    if not modality:
        logger.warning(f"No modality specified for drift analysis on {policy_id}")
    
    # Build query filter
    filter_conditions = [FieldCondition(key="policy_id", match=MatchValue(value=policy_id))]
    if modality:
        filter_conditions.append(FieldCondition(key="modality", match=MatchValue(value=modality)))
    
    # Retrieve all embeddings grouped by year
    years_data = {}
    offset = None
    
    while True:
        batch_points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=filter_conditions),
            limit=100,
            offset=offset,
            with_vectors=True,
            with_payload=True
        )
        
        if not batch_points:
            break
        
        for point in batch_points:
            year = point.payload.get("year")
            if year:
                if year not in years_data:
                    years_data[year] = []
                years_data[year].append(point.vector)
        
        if next_offset is None:
            break
        offset = next_offset
    
    # Validate minimum data requirements
    if len(years_data) < MIN_YEARS_FOR_TIMELINE:
        logger.warning(
            f"Insufficient data for drift analysis: only {len(years_data)} years found"
        )
        return None
    
    # Filter and validate years
    valid_years = {}
    for year, vectors in years_data.items():
        if len(vectors) >= MIN_SAMPLES_PER_YEAR:
            try:
                year_int = int(year)
                valid_years[year_int] = vectors
            except ValueError:
                logger.warning(f"Invalid year format: {year}")
        else:
            logger.warning(f"Year {year} has insufficient samples: {len(vectors)}")
    
    if len(valid_years) < MIN_YEARS_FOR_TIMELINE:
        logger.warning(f"After filtering, only {len(valid_years)} valid years remain")
        return None
    
    # Compute drift between consecutive years
    sorted_years = sorted(valid_years.keys())
    timeline = []
    
    for year_idx in range(len(sorted_years) - 1):
        year_from = sorted_years[year_idx]
        year_to = sorted_years[year_idx + 1]
        
        vectors_from = np.array(valid_years[year_from])
        vectors_to = np.array(valid_years[year_to])
        
        # Compute centroids (mean of all embeddings for each year)
        centroid_from = np.mean(vectors_from, axis=0)
        centroid_to = np.mean(vectors_to, axis=0)
        
        # Normalize for cosine similarity
        centroid_from_norm = centroid_from / np.linalg.norm(centroid_from)
        centroid_to_norm = centroid_to / np.linalg.norm(centroid_to)
        
        # Compute cosine similarity and convert to drift score
        similarity = np.dot(centroid_from_norm, centroid_to_norm)
        # clip similarity to valid range - saw NaN once with zero vectors
        similarity = np.clip(similarity, *VECTOR_SIMILARITY_BOUNDS)
        drift_score = 1.0 - similarity
        
        # Classify severity
        severity = _classify_drift_severity(drift_score)
        
        timeline.append({
            "from_year": str(year_from),
            "to_year": str(year_to),
            "drift_score": float(drift_score),
            "severity": severity,
            "samples_year1": len(vectors_from),
            "samples_year2": len(vectors_to),
            "similarity": float(similarity)
        })
        
        # Log critical drifts for monitoring
        if drift_score > DRIFT_CRITICAL_THRESHOLD:
            logger.warning(
                f"CRITICAL drift detected: {policy_id} {year_from}→{year_to} "
                f"(score={drift_score:.3f}, samples={len(vectors_from)},{len(vectors_to)})"
            )
    
    return timeline


def find_max_drift(
    policy_id: str,
    modality: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Find the period with maximum semantic drift.
    
    Args:
        policy_id: Policy to analyze.
        modality: Optional filter (budget/news/temporal).
        
    Returns:
        Dict with maximum drift period, or None if no drift data exists.
        
    Raises:
        Exception: If analysis fails.
    """
    timeline = compute_drift_timeline(policy_id, modality)
    
    if not timeline or len(timeline) == 0:
        logger.info(f"No drift timeline found for {policy_id}")
        return None
    
    max_period = max(timeline, key=lambda period: period["drift_score"])
    return max_period


def _classify_drift_severity(drift_score: float) -> str:
    """
    Classify drift score into severity categories.
    
    Args:
        drift_score: Float between 0 and 1.
        
    Returns:
        str: One of CRITICAL, HIGH, MEDIUM, LOW, MINIMAL.
    """
    if drift_score > DRIFT_CRITICAL_THRESHOLD:
        return "CRITICAL"
    elif drift_score > DRIFT_HIGH_THRESHOLD:
        return "HIGH"
    elif drift_score > DRIFT_MEDIUM_THRESHOLD:
        return "MEDIUM"
    elif drift_score > DRIFT_LOW_THRESHOLD:
        return "LOW"
    else:
        return "MINIMAL"
