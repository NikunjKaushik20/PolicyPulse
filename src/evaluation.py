def mean_reciprocal_rank(results: list, ground_truth: set) -> float:
    """
    Compute Mean Reciprocal Rank (MRR) for retrieval results.
    Args:
        results: List of retrieved point IDs (ordered)
        ground_truth: Set of relevant point IDs
    Returns:
        float: MRR score
    """
    for rank, pid in enumerate(results, 1):
        if pid in ground_truth:
            return 1.0 / rank
    return 0.0

def hit_rate_at_5(results: list, ground_truth: set) -> float:
    """
    Compute Hit Rate@5 for retrieval results.
    Args:
        results: List of retrieved point IDs (ordered)
        ground_truth: Set of relevant point IDs
    Returns:
        float: Hit rate (0 or 1)
    """
    return 1.0 if any(pid in ground_truth for pid in results[:5]) else 0.0
from .reasoning import generate_reasoning_trace
from .embeddings import embed_text
from .qdrant_setup import get_client, COLLECTION_NAME
from qdrant_client.models import Filter, FieldCondition, MatchValue
import json

def run_evaluation(test_queries: list, policy_id: str):
    results = {
        "total_queries": len(test_queries),
        "correct_year": 0,
        "correct_modality": 0,
        "correct_both": 0,
        "avg_top1_score": 0,
        "details": []
    }
    
    scores = []
    
    for test in test_queries:
        trace = generate_reasoning_trace(
            query=test["query"],
            policy_id=policy_id,
            top_k=3
        )
        
        retrieved = trace.get("retrieved_points", [])
        
        if not retrieved:
            results["details"].append({
                "query": test["query"],
                "status": "NO_RESULTS",
                "expected": test,
                "actual": None
            })
            continue
        
        top = retrieved[0]
        yr_match = top["year"] == test.get("expected_year")
        mod_match = top["modality"] == test.get("expected_modality")
        
        if yr_match:
            results["correct_year"] += 1
        if mod_match:
            results["correct_modality"] += 1
        if yr_match and mod_match:
            results["correct_both"] += 1
        
        scores.append(top["score"])
        
        # figure out status
        if yr_match and mod_match:
            status = "CORRECT"
        elif yr_match or mod_match:
            status = "PARTIAL"
        else:
            status = "WRONG"
        
        results["details"].append({
            "query": test["query"],
            "status": status,
            "expected": test,
            "actual": {
                "year": top["year"],
                "modality": top["modality"],
                "score": top["score"]
            }
        })
    
    if scores:
        results["avg_top1_score"] = round(sum(scores) / len(scores), 3)
    else:
        results["avg_top1_score"] = 0
    
    results["accuracy_year"] = round(results["correct_year"] / results["total_queries"], 3)
    results["accuracy_modality"] = round(results["correct_modality"] / results["total_queries"], 3)
    results["accuracy_both"] = round(results["correct_both"] / results["total_queries"], 3)
    
    return results

def baseline_keyword_search(query: str, policy_id: str, top_k: int = 3):
    # simple search without any smart filtering (baseline comparison)
    client = get_client()
    qvec = embed_text(query)
    
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=qvec,
        query_filter=Filter(must=[FieldCondition(key="policy_id", match=MatchValue(value=policy_id))]),
        limit=top_k,
        with_payload=True
    )
    
    return [{
        "year": r.payload.get("year"),
        "modality": r.payload.get("modality"),
        "score": round(r.score, 4)
    } for r in results]

def compare_with_baseline(test_queries: list, policy_id: str):
    comp = {
        "policypulse": {"correct": 0, "total": len(test_queries)},
        "baseline": {"correct": 0, "total": len(test_queries)},
        "details": []
    }
    
    for test in test_queries:
        # run our smart system
        pp_trace = generate_reasoning_trace(test["query"], policy_id, top_k=1)
        pp_result = pp_trace.get("retrieved_points", [{}])[0]
        
        # run dumb baseline
        baseline_results = baseline_keyword_search(test["query"], policy_id, top_k=1)
        baseline_result = baseline_results[0] if baseline_results else {}
        
        pp_correct = (pp_result.get("year") == test.get("expected_year") and
                      pp_result.get("modality") == test.get("expected_modality"))
        
        baseline_correct = (baseline_result.get("year") == test.get("expected_year") and
                           baseline_result.get("modality") == test.get("expected_modality"))
        
        if pp_correct:
            comp["policypulse"]["correct"] += 1
        if baseline_correct:
            comp["baseline"]["correct"] += 1
        
        # figure out who won
        if pp_correct and not baseline_correct:
            winner = "PolicyPulse"
        elif baseline_correct and not pp_correct:
            winner = "Baseline"
        elif pp_correct and baseline_correct:
            winner = "Tie"
        else:
            winner = "Both Wrong"
        
        comp["details"].append({
            "query": test["query"],
            "expected": test,
            "policypulse": pp_result,
            "baseline": baseline_result,
            "winner": winner
        })
    
    comp["policypulse"]["accuracy"] = round(comp["policypulse"]["correct"] / comp["policypulse"]["total"], 3)
    comp["baseline"]["accuracy"] = round(comp["baseline"]["correct"] / comp["baseline"]["total"], 3)
    comp["improvement"] = round((comp["policypulse"]["accuracy"] - comp["baseline"]["accuracy"]) * 100, 1)
    
    return comp

def save_evaluation_results(results: dict, filename: str):
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✅ Saved evaluation results to {filename}")
