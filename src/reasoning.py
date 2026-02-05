"""
Simplified reasoning module for ChromaDB-based PolicyPulse.

Provides semantic search and answer synthesis without requiring Qdrant.
"""

from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

# TODO: consider caching frequent queries - seeing ~40% repeat rate in logs
# UPDATE 2024-01: tried redis, too heavy for this use case


def generate_reasoning_trace(
    query: str,
    retrieved_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate reasoning trace from ChromaDB query results.
    
    Args:
        query: User's question
        retrieved_results: Results from chromadb_setup.query_documents()
    
    Returns:
        Dict with reasoning steps and synthesized answer
    """
    trace = {
        "query": query,
        "steps": [],
        "retrieved_points": [],
        "final_answer": "",
        "confidence_score": 0.0,
        # debug fields - remove before prod? kept for now
        "_debug_timestamp": None
    }
    
    try:
        # Step 1: Parse retrieved results
        ids = retrieved_results.get('ids', [[]])[0]
        documents = retrieved_results.get('documents', [[]])[0]
        metadatas = retrieved_results.get('metadatas', [[]])[0]
        distances = retrieved_results.get('distances', [[]])[0]
        
        trace["steps"].append({
            "step": 1,
            "action": f"Retrieved {len(documents)} documents from ChromaDB"
        })
        
        # Step 2: Format results for display
        retrieved_points = []
        for i, (doc_id, doc, meta, dist) in enumerate(zip(ids, documents, metadatas, distances)):
            retrieved_points.append({
                "rank": i + 1,
                "id": doc_id,
                "content_preview": doc[:500] if doc else "",
                "policy_id": meta.get("policy_id", "UNKNOWN"),
                "modality": meta.get("modality", "text"),
                "year": meta.get("year", ""),
                "distance": round(dist, 4),
                "score": round(1 - dist, 4)  # Convert distance to similarity
            })
        
        trace["retrieved_points"] = retrieved_points
        
        trace["steps"].append({
            "step": 2,
            "action": "Formatted retrieved documents"
        })
        
        #Step 3: Synthesize answer
        # NOTE: this was originally calling an LLM but we stripped it out
        # retrieval-only is more deterministic anyway
        answer = synthesize_answer(query, retrieved_points)
        trace["final_answer"] = answer
        
        # Step 4: Calculate confidence
        confidence = calculate_confidence(retrieved_points)
        trace["confidence_score"] = confidence
        
        trace["steps"].append({
            "step": 3,
            "action": "Answer synthesized",
            "confidence": confidence
        })
        
    except Exception as e:
        logger.error(f"Reasoning trace generation failed: {e}")
        trace["final_answer"] = f"Error processing query: {str(e)}"
        trace["confidence_score"] = 0.0
    
    return trace


def synthesize_answer(
    query: str,
    retrieved_points: List[Dict[str, Any]]
) -> str:
    """
    Synthesize answer from retrieved documents.
    
    Args:
        query: User's question
        retrieved_points: List of retrieved document dicts
    
    Returns:
        Synthesized answer string
    """
    if not retrieved_points:
        return "No relevant information found. Please try rephrasing your question."
    
    # Determine the primary policy from top results
    policy_counts = {}
    for point in retrieved_points[:3]:
        pid = point.get("policy_id", "UNKNOWN")
        policy_counts[pid] = policy_counts.get(pid, 0) + 1
    
    primary_policy = max(policy_counts, key=policy_counts.get) if policy_counts else None
    
    # Filter to only include results from primary policy
    if primary_policy:
        filtered_points = [p for p in retrieved_points if p.get("policy_id") == primary_policy]
    else:
        filtered_points = retrieved_points
    
    # Group by modality
    by_modality = {}
    for point in filtered_points:
        modality = point.get("modality", "text")
        if modality not in by_modality:
            by_modality[modality] = []
        by_modality[modality].append(point)
    
    # Build answer sections
    sections = []
    
    # Add temporal/text info
    temporal = by_modality.get("temporal") or by_modality.get("text", [])
    if temporal:
        top = temporal[0]
        sections.append(
            f"{top['policy_id']} ({top.get('year', 'N/A')}): {top['content_preview']}"
        )
    
    # Add budget info (only from same policy)
    budget = by_modality.get("budget", [])
    if budget:
        top = budget[0]
        sections.append(
            f"Budget ({top.get('year', 'N/A')}): {top['content_preview']}"
        )
    
    # Add news info (only from same policy)
    news = by_modality.get("news", [])
    if news:
        top = news[0]
        sections.append(
            f"News ({top.get('year', 'N/A')}): {top['content_preview']}"
        )
    
    # If no specific modalities, use top result
    if not sections and filtered_points:
        top = filtered_points[0]
        sections.append(f"{top['content_preview']}")
    
    return "\n\n".join(sections) if sections else "No detailed information available."


def calculate_confidence(retrieved_points: List[Dict[str, Any]]) -> float:
    """
    Calculate confidence based on retrieval scores and result consistency.
    
    Args:
        retrieved_points: List of retrieved documents
    
    Returns:
        Confidence score (0-1)
    """
    if not retrieved_points:
        return 0.0
    
    # Base confidence from top 3 scores
    top_scores = [p.get("score", 0) for p in retrieved_points[:3]]
    base_confidence = sum(top_scores) / len(top_scores) if top_scores else 0.0
    
    # Boost confidence if all top results are from the same policy (consistent)
    policies = [p.get("policy_id") for p in retrieved_points[:3]]
    if len(set(policies)) == 1 and policies[0] is not None:
        # All from same policy = boost by 0.15
        base_confidence = min(base_confidence + 0.15, 1.0)
    
    # Boost if we have multiple modalities (comprehensive answer)
    modalities = set(p.get("modality") for p in retrieved_points[:5])
    if len(modalities) >= 2:
        base_confidence = min(base_confidence + 0.1, 1.0)
    
    return round(min(base_confidence, 1.0), 3)
