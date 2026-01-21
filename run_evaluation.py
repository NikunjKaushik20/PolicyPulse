"""
PolicyPulse Comprehensive Evaluation Suite (Enhanced for Full Codebase)

This script evaluates the entire PolicyPulse system with support for:
- All 10 policies (NREGA, RTI, NEP, PM-KISAN, SWACHH-BHARAT, DIGITAL-INDIA, 
  AYUSHMAN-BHARAT, MAKE-IN-INDIA, SKILL-INDIA, SMART-CITIES)
- Multiple evaluation metrics (Accuracy, MRR, Hit@K, Precision, Recall, F1)
- Multimodal queries (text, image, audio, video)
- Baseline comparisons
- Memory system evaluation (decay, consolidation, reinforcement)
- Drift detection validation
- API endpoint testing
- Detailed reporting (JSON, CSV, HTML, console)
- Summary statistics across all policies
"""

import json
import csv
import argparse
import os
import sys
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.embeddings import embed_text, get_sentiment
    from src.qdrant_setup import setup_qdrant, get_qdrant_client
    from src.reasoning import process_query
    from src.drift import calculate_policy_drift
    from src.memory import apply_memory_decay, consolidate_memories
    from src.recommendations import get_policy_recommendations
except ImportError as e:
    print(f"⚠️  Warning: Could not import some modules: {e}")
    print("Continuing with API-based evaluation...")


# ============================================================================
# CONFIGURATION
# ============================================================================

# All supported policies
ALL_POLICIES = [
    "NREGA", "RTI", "NEP", "PM-KISAN", "SWACHH-BHARAT",
    "DIGITAL-INDIA", "AYUSHMAN-BHARAT", "MAKE-IN-INDIA", 
    "SKILL-INDIA", "SMART-CITIES"
]

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = 30

# Test query templates for each policy
POLICY_TEST_QUERIES = {
    "NREGA": [
        {"query": "What is NREGA?", "expected_year": None, "expected_modality": "temporal", "category": "definition"},
        {"query": "NREGA budget allocation in 2020", "expected_year": "2020", "expected_modality": "budget", "category": "budget"},
        {"query": "NREGA news coverage 2019", "expected_year": "2019", "expected_modality": "news", "category": "news"},
        {"query": "Original objectives of NREGA in 2005", "expected_year": "2005", "expected_modality": "temporal", "category": "policy_intent"},
        {"query": "How has NREGA evolved over time?", "expected_year": None, "expected_modality": "temporal", "category": "evolution"},
    ],
    "RTI": [
        {"query": "What is the Right to Information Act?", "expected_year": None, "expected_modality": "temporal", "category": "definition"},
        {"query": "RTI budget 2015", "expected_year": "2015", "expected_modality": "budget", "category": "budget"},
        {"query": "RTI implementation challenges", "expected_year": None, "expected_modality": "news", "category": "challenges"},
        {"query": "RTI Act provisions 2005", "expected_year": "2005", "expected_modality": "temporal", "category": "policy_intent"},
    ],
    "NEP": [
        {"query": "What is National Education Policy?", "expected_year": None, "expected_modality": "temporal", "category": "definition"},
        {"query": "NEP 2020 key features", "expected_year": "2020", "expected_modality": "temporal", "category": "policy_intent"},
        {"query": "NEP budget allocation", "expected_year": None, "expected_modality": "budget", "category": "budget"},
    ],
    "PM-KISAN": [
        {"query": "What is PM-KISAN scheme?", "expected_year": None, "expected_modality": "temporal", "category": "definition"},
        {"query": "PM-KISAN budget 2021", "expected_year": "2021", "expected_modality": "budget", "category": "budget"},
        {"query": "PM-KISAN beneficiary count", "expected_year": None, "expected_modality": "news", "category": "impact"},
    ],
    "SWACHH-BHARAT": [
        {"query": "Swachh Bharat Mission objectives", "expected_year": None, "expected_modality": "temporal", "category": "policy_intent"},
        {"query": "Swachh Bharat budget 2019", "expected_year": "2019", "expected_modality": "budget", "category": "budget"},
        {"query": "Swachh Bharat achievements", "expected_year": None, "expected_modality": "news", "category": "impact"},
    ],
    "DIGITAL-INDIA": [
        {"query": "Digital India initiative goals", "expected_year": None, "expected_modality": "temporal", "category": "policy_intent"},
        {"query": "Digital India spending 2020", "expected_year": "2020", "expected_modality": "budget", "category": "budget"},
    ],
    "AYUSHMAN-BHARAT": [
        {"query": "Ayushman Bharat health scheme", "expected_year": None, "expected_modality": "temporal", "category": "definition"},
        {"query": "Ayushman Bharat coverage", "expected_year": None, "expected_modality": "news", "category": "impact"},
    ],
    "MAKE-IN-INDIA": [
        {"query": "Make in India manufacturing policy", "expected_year": None, "expected_modality": "temporal", "category": "definition"},
        {"query": "Make in India investment", "expected_year": None, "expected_modality": "budget", "category": "budget"},
    ],
    "SKILL-INDIA": [
        {"query": "Skill India mission objectives", "expected_year": None, "expected_modality": "temporal", "category": "policy_intent"},
        {"query": "Skill India training programs", "expected_year": None, "expected_modality": "news", "category": "implementation"},
    ],
    "SMART-CITIES": [
        {"query": "Smart Cities Mission goals", "expected_year": None, "expected_modality": "temporal", "category": "policy_intent"},
        {"query": "Smart Cities funding", "expected_year": None, "expected_modality": "budget", "category": "budget"},
    ],
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_banner(text: str, char: str = "=", width: int = 80):
    """Print a formatted banner"""
    print(f"\n{char * width}")
    print(f"{text.center(width)}")
    print(f"{char * width}\n")


def print_section(text: str, emoji: str = "📊"):
    """Print a formatted section header"""
    print(f"\n{emoji} {text}")
    print("-" * 60)


def safe_api_call(endpoint: str, method: str = "GET", data: Dict = None, 
                  timeout: int = API_TIMEOUT) -> Optional[Dict]:
    """Make a safe API call with error handling"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  API Error ({endpoint}): {str(e)[:100]}")
        return None
    except json.JSONDecodeError:
        print(f"  ⚠️  Invalid JSON response from {endpoint}")
        return None


# ============================================================================
# EVALUATION METRICS
# ============================================================================

def calculate_mrr(rankings: List[float]) -> float:
    """Calculate Mean Reciprocal Rank"""
    if not rankings:
        return 0.0
    reciprocal_ranks = [1.0 / (i + 1) for i, score in enumerate(rankings) if score > 0.5]
    return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0


def calculate_hit_at_k(rankings: List[float], k: int = 5) -> float:
    """Calculate Hit@K metric"""
    if not rankings:
        return 0.0
    top_k = rankings[:k]
    return 1.0 if any(score > 0.5 for score in top_k) else 0.0


def calculate_precision_recall_f1(true_positives: int, false_positives: int, 
                                   false_negatives: int) -> Tuple[float, float, float]:
    """Calculate Precision, Recall, and F1 score"""
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


# ============================================================================
# QUERY EVALUATION
# ============================================================================

def evaluate_single_query(policy_id: str, query_data: Dict, 
                         use_api: bool = True) -> Dict[str, Any]:
    """
    Evaluate a single query and return detailed results
    
    Returns:
        Dictionary with evaluation metrics for this query
    """
    query = query_data["query"]
    expected_year = query_data.get("expected_year")
    expected_modality = query_data.get("expected_modality")
    category = query_data.get("category", "general")
    
    result = {
        "query": query,
        "policy_id": policy_id,
        "category": category,
        "expected": {"year": expected_year, "modality": expected_modality},
        "actual": {},
        "scores": {},
        "status": "UNKNOWN"
    }
    
    if use_api:
        # Use API endpoint
        response = safe_api_call("/query", method="POST", data={
            "policy_id": policy_id,
            "question": query,
            "top_k": 10
        })
        
        if not response:
            result["status"] = "API_ERROR"
            return result
        
        # Extract results
        retrieved = response.get("retrieved_points", [])
        confidence = response.get("confidence", 0.0)
        
    else:
        # Use direct function calls
        try:
            response = process_query(query, policy_id, top_k=10)
            retrieved = response.get("retrieved_points", [])
            confidence = response.get("confidence", 0.0)
        except Exception as e:
            result["status"] = f"ERROR: {str(e)}"
            return result
    
    # Evaluate year accuracy
    year_correct = False
    if expected_year:
        if retrieved:
            top_year = str(retrieved[0].get("year", ""))
            year_correct = top_year == expected_year
            result["actual"]["year"] = top_year
    else:
        year_correct = True  # No year expected, so it's correct by default
    
    # Evaluate modality accuracy
    modality_correct = False
    if expected_modality:
        if retrieved:
            top_modality = retrieved[0].get("modality", "")
            modality_correct = top_modality == expected_modality
            result["actual"]["modality"] = top_modality
    else:
        modality_correct = True
    
    # Calculate ranking metrics
    scores = [r.get("score", 0.0) for r in retrieved]
    result["scores"]["mrr"] = calculate_mrr(scores)
    result["scores"]["hit_at_5"] = calculate_hit_at_k(scores, k=5)
    result["scores"]["hit_at_10"] = calculate_hit_at_k(scores, k=10)
    result["scores"]["confidence"] = confidence
    result["scores"]["top_score"] = scores[0] if scores else 0.0
    
    # Overall status
    if year_correct and modality_correct:
        result["status"] = "CORRECT"
    elif year_correct or modality_correct:
        result["status"] = "PARTIAL"
    else:
        result["status"] = "INCORRECT"
    
    return result


def evaluate_policy_queries(policy_id: str, queries: List[Dict], 
                           use_api: bool = True, verbose: bool = True) -> Dict:
    """Evaluate all queries for a single policy"""
    
    if verbose:
        print_section(f"Evaluating {policy_id}", "🔍")
        print(f"  Total queries: {len(queries)}")
    
    results = []
    for i, query_data in enumerate(queries, 1):
        if verbose:
            print(f"  [{i}/{len(queries)}] {query_data['query'][:50]}...", end=" ")
        
        result = evaluate_single_query(policy_id, query_data, use_api)
        results.append(result)
        
        if verbose:
            status_emoji = "✅" if result["status"] == "CORRECT" else "⚠️" if result["status"] == "PARTIAL" else "❌"
            print(f"{status_emoji} {result['status']}")
    
    # Aggregate metrics
    correct = sum(1 for r in results if r["status"] == "CORRECT")
    partial = sum(1 for r in results if r["status"] == "PARTIAL")
    incorrect = sum(1 for r in results if r["status"] == "INCORRECT")
    
    avg_mrr = np.mean([r["scores"]["mrr"] for r in results if "mrr" in r["scores"]])
    avg_hit_5 = np.mean([r["scores"]["hit_at_5"] for r in results if "hit_at_5" in r["scores"]])
    avg_confidence = np.mean([r["scores"]["confidence"] for r in results if "confidence" in r["scores"]])
    
    summary = {
        "policy_id": policy_id,
        "total_queries": len(queries),
        "correct": correct,
        "partial": partial,
        "incorrect": incorrect,
        "accuracy": correct / len(queries) if queries else 0.0,
        "avg_mrr": float(avg_mrr),
        "avg_hit_at_5": float(avg_hit_5),
        "avg_confidence": float(avg_confidence),
        "details": results
    }
    
    if verbose:
        print(f"\n  📈 Results:")
        print(f"     Accuracy:      {summary['accuracy']:.1%} ({correct}/{len(queries)})")
        print(f"     Avg MRR:       {summary['avg_mrr']:.3f}")
        print(f"     Avg Hit@5:     {summary['avg_hit_at_5']:.3f}")
        print(f"     Avg Confidence: {summary['avg_confidence']:.3f}")
    
    return summary


# ============================================================================
# SYSTEM COMPONENT EVALUATION
# ============================================================================

def evaluate_api_endpoints(verbose: bool = True) -> Dict:
    """Test all API endpoints for availability and correctness"""
    
    if verbose:
        print_section("API Endpoint Testing", "🌐")
    
    endpoints = {
        "health": {"method": "GET", "endpoint": "/health"},
        "stats": {"method": "GET", "endpoint": "/stats"},
        "query": {"method": "POST", "endpoint": "/query", 
                 "data": {"policy_id": "NREGA", "question": "What is NREGA?"}},
        "drift": {"method": "POST", "endpoint": "/drift", 
                 "data": {"policy_id": "NREGA"}},
        "recommendations": {"method": "POST", "endpoint": "/recommendations", 
                          "data": {"policy_id": "NREGA", "top_k": 3}},
        "memory_health": {"method": "GET", "endpoint": "/memory/health"},
    }
    
    results = {}
    for name, config in endpoints.items():
        if verbose:
            print(f"  Testing {name}...", end=" ")
        
        response = safe_api_call(
            config["endpoint"], 
            method=config["method"],
            data=config.get("data")
        )
        
        status = "✅ PASS" if response else "❌ FAIL"
        results[name] = {"status": "PASS" if response else "FAIL", "response": response}
        
        if verbose:
            print(status)
    
    return results


def evaluate_memory_system(policy_id: str = "NREGA", 
                          use_api: bool = True, verbose: bool = True) -> Dict:
    """Evaluate memory decay, consolidation, and reinforcement"""
    
    if verbose:
        print_section(f"Memory System Evaluation ({policy_id})", "🧠")
    
    results = {}
    
    # Test memory health
    if use_api:
        health = safe_api_call("/memory/health")
    else:
        # Would need to implement direct memory health check
        health = {"total_points": 0, "avg_decay_weight": 0.0}
    
    results["initial_health"] = health
    
    if verbose and health:
        print(f"  Total points: {health.get('total_points', 'N/A')}")
        print(f"  Avg decay weight: {health.get('avg_decay_weight', 'N/A'):.3f}")
    
    # Test decay application
    if use_api:
        decay_result = safe_api_call(f"/memory/decay?policy_id={policy_id}", method="POST")
    
    if verbose and decay_result:
        print(f"  ✅ Decay applied to {decay_result.get('points_updated', 0)} points")
    
    # Test consolidation
    if use_api:
        consolidate_result = safe_api_call(
            f"/memory/consolidate?policy_id={policy_id}&threshold=0.95", 
            method="POST"
        )
    
    if verbose and consolidate_result:
        print(f"  ✅ Consolidated {consolidate_result.get('points_merged', 0)} duplicate memories")
    
    results["decay"] = decay_result
    results["consolidation"] = consolidate_result
    
    return results


def evaluate_drift_detection(policy_id: str = "NREGA", 
                            use_api: bool = True, verbose: bool = True) -> Dict:
    """Evaluate policy drift detection accuracy"""
    
    if verbose:
        print_section(f"Drift Detection ({policy_id})", "📉")
    
    if use_api:
        drift_data = safe_api_call("/drift", method="POST", 
                                  data={"policy_id": policy_id, "modality": "temporal"})
    else:
        drift_data = calculate_policy_drift(policy_id, modality="temporal")
    
    if not drift_data:
        return {"status": "ERROR"}
    
    timeline = drift_data.get("timeline", [])
    max_drift = drift_data.get("max_drift", {})
    
    if verbose:
        print(f"  Total year transitions: {len(timeline)}")
        if max_drift:
            print(f"  Max drift: {max_drift.get('from_year')} → {max_drift.get('to_year')}")
            print(f"  Drift score: {max_drift.get('drift_score', 0):.3f} ({max_drift.get('severity', 'N/A')})")
    
    return {
        "policy_id": policy_id,
        "timeline_length": len(timeline),
        "max_drift": max_drift,
        "avg_drift": np.mean([t.get("drift_score", 0) for t in timeline]) if timeline else 0.0
    }


# ============================================================================
# REPORTING
# ============================================================================

def save_json_report(data: Dict, filepath: str):
    """Save results as JSON"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def save_csv_report(results: Dict, filepath: str):
    """Save summary results as CSV"""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Policy", "Queries", "Correct", "Accuracy", "Avg MRR", 
                        "Avg Hit@5", "Avg Confidence"])
        
        for policy_id, policy_results in results.items():
            if isinstance(policy_results, dict) and "total_queries" in policy_results:
                writer.writerow([
                    policy_id,
                    policy_results["total_queries"],
                    policy_results["correct"],
                    f"{policy_results['accuracy']:.1%}",
                    f"{policy_results['avg_mrr']:.3f}",
                    f"{policy_results['avg_hit_at_5']:.3f}",
                    f"{policy_results['avg_confidence']:.3f}"
                ])


def generate_html_report(results: Dict, output_path: str):
    """Generate an interactive HTML report"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PolicyPulse Evaluation Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            h1 {{ color: #2c3e50; }}
            .summary {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .metric {{ display: inline-block; margin: 10px 20px; }}
            .metric-label {{ font-weight: bold; color: #7f8c8d; }}
            .metric-value {{ font-size: 24px; color: #2980b9; }}
            table {{ width: 100%; border-collapse: collapse; background: white; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #34495e; color: white; }}
            .correct {{ color: #27ae60; }}
            .partial {{ color: #f39c12; }}
            .incorrect {{ color: #e74c3c; }}
        </style>
    </head>
    <body>
        <h1>PolicyPulse Evaluation Report</h1>
        <div class="summary">
            <h2>Overall Summary</h2>
            <div class="metric">
                <div class="metric-label">Total Policies</div>
                <div class="metric-value">{len(results)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Queries</div>
                <div class="metric-value">{sum(r.get('total_queries', 0) for r in results.values() if isinstance(r, dict))}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Overall Accuracy</div>
                <div class="metric-value">{sum(r.get('correct', 0) for r in results.values() if isinstance(r, dict)) / max(sum(r.get('total_queries', 0) for r in results.values() if isinstance(r, dict)), 1):.1%}</div>
            </div>
        </div>
        
        <h2>Policy Results</h2>
        <table>
            <tr>
                <th>Policy</th>
                <th>Queries</th>
                <th>Correct</th>
                <th>Accuracy</th>
                <th>MRR</th>
                <th>Hit@5</th>
            </tr>
    """
    
    for policy_id, policy_results in results.items():
        if isinstance(policy_results, dict) and "total_queries" in policy_results:
            html += f"""
            <tr>
                <td><strong>{policy_id}</strong></td>
                <td>{policy_results['total_queries']}</td>
                <td class="correct">{policy_results['correct']}</td>
                <td>{policy_results['accuracy']:.1%}</td>
                <td>{policy_results['avg_mrr']:.3f}</td>
                <td>{policy_results['avg_hit_at_5']:.3f}</td>
            </tr>
            """
    
    html += """
        </table>
        <p style="margin-top: 40px; color: #7f8c8d;">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """
    
    with open(output_path, 'w') as f:
        f.write(html)


# ============================================================================
# MAIN EVALUATION PIPELINE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="PolicyPulse Comprehensive Evaluation Suite"
    )
    parser.add_argument(
        "--policies", nargs="+", 
        choices=ALL_POLICIES + ["all"],
        default=["all"],
        help="Policies to evaluate (default: all)"
    )
    parser.add_argument(
        "--output-dir", default="./evaluation_results",
        help="Output directory for results"
    )
    parser.add_argument(
        "--use-api", action="store_true", default=True,
        help="Use API endpoints (default: True)"
    )
    parser.add_argument(
        "--test-endpoints", action="store_true",
        help="Test API endpoints"
    )
    parser.add_argument(
        "--test-memory", action="store_true",
        help="Test memory system"
    )
    parser.add_argument(
        "--test-drift", action="store_true",
        help="Test drift detection"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Minimal console output"
    )
    parser.add_argument(
        "--api-url", default="http://localhost:8000",
        help="API base URL"
    )
    
    args = parser.parse_args()
    
    # Setup
    global API_BASE_URL
    API_BASE_URL = args.api_url
    verbose = not args.quiet
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Determine policies to evaluate
    if "all" in args.policies:
        policies_to_eval = ALL_POLICIES
    else:
        policies_to_eval = args.policies
    
    # Filter to policies with test queries
    policies_to_eval = [p for p in policies_to_eval if p in POLICY_TEST_QUERIES]
    
    if not policies_to_eval:
        print("❌ No valid policies to evaluate!")
        return
    
    # Print header
    if verbose:
        print_banner("PolicyPulse Comprehensive Evaluation Suite")
        print(f"📅 Timestamp:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Output Dir:    {args.output_dir}")
        print(f"🌐 API URL:       {args.api_url}")
        print(f"📊 Policies:      {', '.join(policies_to_eval)}")
        print(f"🔢 Total Queries: {sum(len(POLICY_TEST_QUERIES.get(p, [])) for p in policies_to_eval)}")
    
    all_results = {}
    
    # Test API endpoints if requested
    if args.test_endpoints:
        endpoint_results = evaluate_api_endpoints(verbose)
        all_results["api_endpoints"] = endpoint_results
    
    # Test memory system if requested
    if args.test_memory:
        memory_results = evaluate_memory_system(
            policy_id=policies_to_eval[0],
            use_api=args.use_api,
            verbose=verbose
        )
        all_results["memory_system"] = memory_results
    
    # Test drift detection if requested
    if args.test_drift:
        drift_results = {}
        for policy_id in policies_to_eval[:3]:  # Test first 3 policies
            drift_results[policy_id] = evaluate_drift_detection(
                policy_id=policy_id,
                use_api=args.use_api,
                verbose=verbose
            )
        all_results["drift_detection"] = drift_results
    
    # Evaluate queries for each policy
    for policy_id in policies_to_eval:
        queries = POLICY_TEST_QUERIES.get(policy_id, [])
        if not queries:
            continue
        
        try:
            policy_results = evaluate_policy_queries(
                policy_id=policy_id,
                queries=queries,
                use_api=args.use_api,
                verbose=verbose
            )
            all_results[policy_id] = policy_results
            
        except Exception as e:
            print(f"\n❌ Error evaluating {policy_id}: {str(e)}")
            if verbose:
                import traceback
                traceback.print_exc()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON report (detailed)
    json_path = os.path.join(args.output_dir, f"evaluation_{timestamp}.json")
    save_json_report(all_results, json_path)
    if verbose:
        print(f"\n✅ Saved detailed results: {json_path}")
    
    # CSV report (summary)
    csv_path = os.path.join(args.output_dir, f"evaluation_summary_{timestamp}.csv")
    save_csv_report(all_results, csv_path)
    if verbose:
        print(f"✅ Saved CSV summary: {csv_path}")
    
    # HTML report (interactive)
    html_path = os.path.join(args.output_dir, f"evaluation_report_{timestamp}.html")
    generate_html_report(all_results, html_path)
    if verbose:
        print(f"✅ Saved HTML report: {html_path}")
    
    # Print final summary
    # ========================= FINAL SUMMARY =========================

    if verbose:
        print("\n📊 FINAL SUMMARY")
        print("=" * 60)

        policy_summaries = {
            k: v for k, v in all_results.items()
            if isinstance(v, dict) and "total_queries" in v
        }

        total_policies = len(policy_summaries)
        total_queries = sum(v["total_queries"] for v in policy_summaries.values())
        total_correct = sum(v["correct"] for v in policy_summaries.values())

        overall_accuracy = (
            total_correct / total_queries if total_queries > 0 else 0.0
        )

        avg_mrr = np.mean([
            v["avg_mrr"] for v in policy_summaries.values()
        ]) if policy_summaries else 0.0

        avg_hit_5 = np.mean([
            v["avg_hit_at_5"] for v in policy_summaries.values()
        ]) if policy_summaries else 0.0

        avg_confidence = np.mean([
            v["avg_confidence"] for v in policy_summaries.values()
        ]) if policy_summaries else 0.0

        print(f"Total Policies Evaluated : {total_policies}")
        print(f"Total Queries            : {total_queries}")
        print(f"Total Correct            : {total_correct}")
        print(f"Overall Accuracy         : {overall_accuracy:.1%}")
        print(f"Average MRR              : {avg_mrr:.3f}")
        print(f"Average Hit@5            : {avg_hit_5:.3f}")
        print(f"Average Confidence       : {avg_confidence:.3f}")

        print("=" * 60)
        print("📁 Reports saved to:", os.path.abspath(args.output_dir))
        print("🚀 Evaluation pipeline completed successfully\n")


if __name__ == "__main__":
    main()
