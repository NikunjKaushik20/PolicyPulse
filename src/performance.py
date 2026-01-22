"""
Performance tracking and monitoring utilities for PolicyPulse.

Provides decorators and utilities to measure and log query performance,
helping demonstrate scalability for hackathon evaluation.
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, Callable
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Global performance stats storage
_performance_stats = {
    "query_times": [],
    "drift_times": [],
    "recommendation_times": [],
    "total_queries": 0,
    "total_drifts": 0,
    "total_recommendations": 0,
    "start_time": datetime.now()
}


def timing_decorator(operation_type: str = "query") -> Callable:
    """
    Decorator to measure and log execution time of functions.
    
    Args:
        operation_type: Type of operation (query/drift/recommendation).
        
    Returns:
        Decorated function that logs execution time.
        
    Example:
        @timing_decorator("query")
        def my_query_function():
            # ... query logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Log performance
                logger.info(f"{operation_type.upper()} completed in {elapsed_ms:.2f}ms")
                
                # Store metrics
                _performance_stats[f"{operation_type}_times"].append(elapsed_ms)
                _performance_stats[f"total_{operation_type}s"] += 1
                
                # Add timing to result if it's a dict
                if isinstance(result, dict):
                    result["query_time_ms"] = round(elapsed_ms, 2)
                
                return result
                
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.error(f"{operation_type.upper()} failed after {elapsed_ms:.2f}ms: {e}")
                raise
        
        return wrapper
    return decorator


def log_query_performance(
    operation_type: str,
    duration_ms: float,
    points_searched: int = None,
    **metadata
) -> None:
    """
    Log performance metrics for a specific operation.
    
    Args:
        operation_type: Type of operation (query/drift/recommendation).
        duration_ms: Duration in milliseconds.
        points_searched: Number of vector points searched.
        **metadata: Additional metadata to log.
    """
    log_data = {
        "operation": operation_type,
        "duration_ms": round(duration_ms, 2),
        "timestamp": datetime.now().isoformat()
    }
    
    if points_searched:
        log_data["points_searched"] = points_searched
    
    log_data.update(metadata)
    
    logger.info(f"Performance: {log_data}")
    
    # Store in stats
    if f"{operation_type}_times" in _performance_stats:
        _performance_stats[f"{operation_type}_times"].append(duration_ms)


def get_performance_stats() -> Dict[str, Any]:
    """
    Get aggregated performance statistics.
    
    Returns:
        Dict containing:
            - average_query_time_ms: Average query latency
            - total_queries: Total queries served
            - uptime_seconds: System uptime
            - queries_per_minute: Throughput rate
    """
    uptime = (datetime.now() - _performance_stats["start_time"]).total_seconds()
    
    stats = {
        "uptime_seconds": round(uptime, 2),
        "total_queries": _performance_stats["total_queries"],
        "total_drifts": _performance_stats["total_drifts"],
        "total_recommendations": _performance_stats["total_recommendations"]
    }
    
    # Calculate averages for each operation type
    for op_type in ["query", "drift", "recommendation"]:
        times = _performance_stats.get(f"{op_type}_times", [])
        if times:
            stats[f"average_{op_type}_time_ms"] = round(sum(times) / len(times), 2)
            stats[f"min_{op_type}_time_ms"] = round(min(times), 2)
            stats[f"max_{op_type}_time_ms"] = round(max(times), 2)
        else:
            stats[f"average_{op_type}_time_ms"] = 0
            stats[f"min_{op_type}_time_ms"] = 0
            stats[f"max_{op_type}_time_ms"] = 0
    
    # Calculate throughput (queries per minute)
    if uptime > 0:
        total_operations = (
            stats["total_queries"] + 
            stats["total_drifts"] + 
            stats["total_recommendations"]
        )
        stats["operations_per_minute"] = round((total_operations / uptime) * 60, 2)
    else:
        stats["operations_per_minute"] = 0
    
    return stats


def reset_performance_stats() -> None:
    """Reset all performance statistics. Useful for testing."""
    global _performance_stats
    _performance_stats = {
        "query_times": [],
        "drift_times": [],
        "recommendation_times": [],
        "total_queries": 0,
        "total_drifts": 0,
        "total_recommendations": 0,
        "start_time": datetime.now()
    }
    logger.info("Performance statistics reset")


def format_performance_summary() -> str:
    """
    Format performance stats as a human-readable string.
    
    Returns:
        Formatted string with performance summary.
    """
    stats = get_performance_stats()
    
    summary = f"""
Performance Summary
===================
Uptime: {stats['uptime_seconds']:.0f}s
Total Operations: {stats['total_queries'] + stats['total_drifts'] + stats['total_recommendations']}
Throughput: {stats['operations_per_minute']:.2f} ops/min

Query Performance:
  - Average: {stats['average_query_time_ms']:.2f}ms
  - Min: {stats['min_query_time_ms']:.2f}ms
  - Max: {stats['max_query_time_ms']:.2f}ms
  - Count: {stats['total_queries']}

Drift Analysis Performance:
  - Average: {stats['average_drift_time_ms']:.2f}ms
  - Count: {stats['total_drifts']}

Recommendations Performance:
  - Average: {stats['average_recommendation_time_ms']:.2f}ms
  - Count: {stats['total_recommendations']}
"""
    return summary.strip()
