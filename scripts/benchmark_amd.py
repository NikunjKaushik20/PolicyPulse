"""
PolicyPulse — AMD Hardware Benchmark Script.

Measures real GPU vs CPU performance across all compute-heavy workloads.
Designed to produce verifiable, judge-ready performance evidence.

Usage:
    python -m scripts.benchmark_amd          # Run all benchmarks
    python -m scripts.benchmark_amd --quick  # Quick mode (fewer iterations)

Output:
    - Console table with timings
    - JSON report at logs/amd_benchmark.json
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime

# Set AMD env vars before torch import
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


# ─────────────────────────────────────────────────────────────────────────────
# Benchmark helpers
# ─────────────────────────────────────────────────────────────────────────────

def _time_fn(fn, *args, warmup=1, iterations=5, **kwargs):
    """Time a function with warmup runs. Returns (avg_ms, min_ms, max_ms)."""
    # Warmup
    for _ in range(warmup):
        fn(*args, **kwargs)

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        times.append(elapsed_ms)

    return {
        "avg_ms": round(sum(times) / len(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "iterations": iterations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Individual benchmarks
# ─────────────────────────────────────────────────────────────────────────────

def bench_text_embedding(iterations=5):
    """Benchmark text embedding (SentenceTransformer on DEVICE)."""
    from src.embeddings import embed_text, embed_batch
    from src.config import DEVICE, EMBED_BATCH_SIZE

    sample_text = (
        "The Mahatma Gandhi National Rural Employment Guarantee Act provides "
        "100 days of guaranteed wage employment to rural households."
    )
    batch_texts = [sample_text] * 32

    single = _time_fn(embed_text, sample_text, iterations=iterations)
    batch = _time_fn(embed_batch, batch_texts, iterations=iterations)

    return {
        "name": "Text Embedding (MiniLM-L6-v2)",
        "device": DEVICE,
        "single_text": single,
        "batch_32": batch,
        "batch_size_config": EMBED_BATCH_SIZE,
        "throughput_texts_per_sec": round(32 / (batch["avg_ms"] / 1000), 1),
    }


def bench_sentiment(iterations=5):
    """Benchmark sentiment analysis (RoBERTa on DEVICE)."""
    from src.embeddings import get_sentiment
    from src.config import DEVICE

    sample_text = "This government scheme has helped millions of farmers."

    result = _time_fn(get_sentiment, sample_text, iterations=iterations)

    return {
        "name": "Sentiment Analysis (RoBERTa)",
        "device": DEVICE,
        "single_inference": result,
    }


def bench_cosine_similarity(iterations=5):
    """Benchmark GPU vs CPU cosine similarity."""
    from src.config import DEVICE

    # Generate random 384-dim vectors (same as MiniLM output)
    np.random.seed(42)
    vectors_a = np.random.randn(100, 384).astype(np.float32)
    vectors_b = np.random.randn(100, 384).astype(np.float32)

    # CPU path (numpy)
    def _cpu_cosine():
        norms_a = np.linalg.norm(vectors_a, axis=1, keepdims=True)
        norms_b = np.linalg.norm(vectors_b, axis=1, keepdims=True)
        return (vectors_a / norms_a) @ (vectors_b / norms_b).T

    cpu_result = _time_fn(_cpu_cosine, iterations=iterations)

    # GPU path (torch)
    gpu_result = None
    try:
        from src.embeddings import gpu_cosine_similarity_matrix
        gpu_result = _time_fn(
            gpu_cosine_similarity_matrix, vectors_a, vectors_b,
            iterations=iterations
        )
    except Exception as e:
        gpu_result = {"error": str(e)}

    return {
        "name": "Cosine Similarity Matrix (100×100, 384-dim)",
        "device": DEVICE,
        "cpu_numpy": cpu_result,
        "gpu_torch": gpu_result,
        "speedup": (
            round(cpu_result["avg_ms"] / gpu_result["avg_ms"], 2)
            if gpu_result and "avg_ms" in gpu_result and gpu_result["avg_ms"] > 0
            else "N/A"
        ),
    }


def bench_drift_centroids(iterations=5):
    """Benchmark GPU centroid computation for drift analysis."""
    from src.config import DEVICE

    # Simulate 500 embedding vectors (realistic policy corpus per year)
    np.random.seed(42)
    vectors = [np.random.randn(384).astype(np.float32) for _ in range(500)]

    # CPU path
    def _cpu_centroid():
        return np.mean(np.stack(vectors, axis=0), axis=0)

    cpu_result = _time_fn(_cpu_centroid, iterations=iterations)

    # GPU path
    gpu_result = None
    try:
        from src.drift import _compute_centroid_gpu
        gpu_result = _time_fn(_compute_centroid_gpu, vectors, iterations=iterations)
    except Exception as e:
        gpu_result = {"error": str(e)}

    return {
        "name": "Drift Centroid (500 vectors × 384-dim)",
        "device": DEVICE,
        "cpu_numpy": cpu_result,
        "gpu_torch": gpu_result,
        "speedup": (
            round(cpu_result["avg_ms"] / gpu_result["avg_ms"], 2)
            if gpu_result and "avg_ms" in gpu_result and gpu_result["avg_ms"] > 0
            else "N/A"
        ),
    }


def bench_worker_scaling():
    """Report worker pool configuration (no timing needed)."""
    from src.config import (
        DEVICE, CPU_CORE_COUNT, OCR_WORKER_COUNT,
        IO_WORKER_COUNT, EMBED_BATCH_SIZE, IMAGE_BATCH_SIZE,
        AUDIO_BATCH_SIZE, GPU_MEMORY_GB, BACKEND_LABEL,
    )
    from src.amd_utils import get_numa_topology

    return {
        "name": "AMD EPYC Worker Scaling",
        "device": DEVICE,
        "backend": BACKEND_LABEL,
        "cpu_cores_logical": CPU_CORE_COUNT,
        "cpu_cores_physical": max(CPU_CORE_COUNT // 2, 1),
        "ocr_workers": OCR_WORKER_COUNT,
        "io_workers": IO_WORKER_COUNT,
        "embed_batch_size": EMBED_BATCH_SIZE,
        "image_batch_size": IMAGE_BATCH_SIZE,
        "audio_batch_size": AUDIO_BATCH_SIZE,
        "gpu_memory_gb": GPU_MEMORY_GB,
        "numa": get_numa_topology(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_benchmarks(quick=False):
    """Run all benchmarks and return structured results."""
    iters = 2 if quick else 5

    print("=" * 64)
    print("  PolicyPulse — AMD Hardware Benchmark")
    print("=" * 64)
    print()

    results = {
        "timestamp": datetime.now().isoformat(),
        "benchmarks": [],
    }

    benchmarks = [
        ("Worker Scaling Config", bench_worker_scaling, {}),
        ("Text Embedding", bench_text_embedding, {"iterations": iters}),
        ("Sentiment Analysis", bench_sentiment, {"iterations": iters}),
        ("Cosine Similarity", bench_cosine_similarity, {"iterations": iters}),
        ("Drift Centroids", bench_drift_centroids, {"iterations": iters}),
    ]

    for label, fn, kwargs in benchmarks:
        print(f"  Running: {label}...", end=" ", flush=True)
        try:
            result = fn(**kwargs)
            results["benchmarks"].append(result)
            print("✅")
        except Exception as e:
            print(f"❌ ({e})")
            results["benchmarks"].append({"name": label, "error": str(e)})

    # Print summary table
    print()
    print("-" * 64)
    print(f"  {'Benchmark':<40} {'Avg (ms)':>10} {'Device':>10}")
    print("-" * 64)

    for b in results["benchmarks"]:
        name = b.get("name", "Unknown")[:40]
        if "single_text" in b:
            # Embedding
            avg = b["single_text"]["avg_ms"]
            dev = b["device"]
            print(f"  {name:<40} {avg:>10.2f} {dev:>10}")
            if "batch_32" in b:
                batch_name = f"  └─ batch(32)"
                bavg = b["batch_32"]["avg_ms"]
                print(f"  {batch_name:<40} {bavg:>10.2f} {dev:>10}")
        elif "single_inference" in b:
            avg = b["single_inference"]["avg_ms"]
            dev = b["device"]
            print(f"  {name:<40} {avg:>10.2f} {dev:>10}")
        elif "cpu_numpy" in b and "gpu_torch" in b:
            cpu_avg = b["cpu_numpy"]["avg_ms"]
            gpu_avg = b["gpu_torch"].get("avg_ms", "N/A") if isinstance(b["gpu_torch"], dict) else "N/A"
            speedup = b.get("speedup", "N/A")
            print(f"  {name:<40} {'':>10} {'':>10}")
            print(f"  {'  └─ CPU (numpy)':<40} {cpu_avg:>10.2f} {'cpu':>10}")
            if isinstance(gpu_avg, (int, float)):
                print(f"  {'  └─ GPU (torch)':<40} {gpu_avg:>10.2f} {'cuda':>10}")
                print(f"  {'  └─ GPU Speedup':<40} {str(speedup) + 'x':>10} {'':>10}")
            else:
                print(f"  {'  └─ GPU (torch)':<40} {'N/A':>10} {'N/A':>10}")
        elif "cpu_cores_logical" in b:
            print(f"  {name:<40} {'':>10} {b['device']:>10}")
            print(f"  {'  └─ Logical cores':<40} {b['cpu_cores_logical']:>10} {'':>10}")
            print(f"  {'  └─ OCR workers':<40} {b['ocr_workers']:>10} {'':>10}")
            print(f"  {'  └─ I/O workers':<40} {b['io_workers']:>10} {'':>10}")
            print(f"  {'  └─ Embed batch':<40} {b['embed_batch_size']:>10} {'':>10}")

    print("-" * 64)
    print()

    # Save JSON report
    os.makedirs("logs", exist_ok=True)
    report_path = "logs/amd_benchmark.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Report saved: {report_path}")
    print()

    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PolicyPulse AMD Benchmark")
    parser.add_argument("--quick", action="store_true", help="Quick mode (2 iterations)")
    args = parser.parse_args()

    run_all_benchmarks(quick=args.quick)
