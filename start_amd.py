"""
PolicyPulse — AMD-Optimized Startup Script.

Startup order:
  1. Detect AMD hardware (ROCm / EPYC)
  2. Set environment variables for best performance
  3. Launch Uvicorn with EPYC-tuned worker count
  4. Print AMD hardware summary for judges

Usage:
    python start_amd.py                # auto-detect workers
    python start_amd.py --workers 32   # explicit worker count
    python start_amd.py --dev          # single-worker dev mode with reload
"""

import os
import sys
import argparse
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# AMD environment tuning BEFORE torch/models are imported
# ─────────────────────────────────────────────────────────────────────────────

# ROCm: Allow PyTorch to use all available VRAM on AMD Instinct
os.environ.setdefault("HSA_ENABLE_SDMA", "0")                # Disable SDMA for better MI-series perf
os.environ.setdefault("PYTORCH_HIP_ALLOC_CONF", "max_split_size_mb:512")

# EPYC: Tune OpenMP / MKL thread count to physical cores
# On EPYC, cpu_count() returns logical (SMT) cores; physical = logical // 2
import os as _os
_logical = _os.cpu_count() or 4
_physical = max(_logical // 2, 1)

os.environ.setdefault("OMP_NUM_THREADS",       str(_physical))
os.environ.setdefault("MKL_NUM_THREADS",       str(_physical))
os.environ.setdefault("OPENBLAS_NUM_THREADS",  str(_physical))
os.environ.setdefault("NUMEXPR_NUM_THREADS",   str(_physical))

# Tokenizers parallel warning suppression
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Print AMD system info
# ─────────────────────────────────────────────────────────────────────────────

def print_amd_banner(info: dict, worker_count: int):
    W = 60
    print("=" * W)
    print("  PolicyPulse — AMD Infrastructure Edition")
    print("=" * W)
    print(f"  Compute Backend : {info.get('backend', 'Unknown')}")
    print(f"  Device          : {info.get('compute_device', 'cpu')}")
    print(f"  ROCm Active     : {info.get('rocm_available', False)}")
    if info.get("rocm_version"):
        print(f"  ROCm Version    : {info['rocm_version']}")
    print(f"  GPU VRAM        : {info.get('gpu_memory_gb', 0):.1f} GiB")
    print(f"  CPU Cores       : {info.get('cpu_cores', 'N/A')} logical")
    print(f"  Uvicorn Workers : {worker_count}")
    print(f"  OCR Workers     : {info.get('ocr_workers', 'N/A')} (EPYC parallel)")
    print(f"  I/O Workers     : {info.get('io_workers', 'N/A')}")
    print(f"  Embed Batch     : {info.get('recommended_batch_size_text', 'N/A')} texts")
    print(f"  Image Batch     : {info.get('recommended_batch_size_image', 'N/A')} images")
    print("-" * W)
    print(f"  API Docs : http://localhost:8000/docs")
    print(f"  AMD Info : http://localhost:8000/amd-info")
    print(f"  Health   : http://localhost:8000/health")
    print("=" * W)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PolicyPulse AMD-Optimized Server")
    parser.add_argument("--workers", type=int, default=None,
                        help="Uvicorn worker count (default: auto based on EPYC cores)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--dev", action="store_true",
                        help="Development mode (1 worker, auto-reload)")
    args = parser.parse_args()

    # Import amd_utils AFTER env vars are set
    from src.amd_utils import get_amd_system_info, get_epyc_core_count, optimal_worker_count

    info = get_amd_system_info()

    if args.dev:
        worker_count = 1
        reload = True
    else:
        # Auto-size: use 1 worker per 2 EPYC physical cores, min 2, max 64
        if args.workers:
            worker_count = args.workers
        else:
            cores = get_epyc_core_count()
            worker_count = max(2, min(cores // 2, 64))
        reload = False

    print_amd_banner(info, worker_count)

    # LAN IP
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"  LAN Access : http://{local_ip}:{args.port}  (use this on mobile)")
        print()
    except Exception:
        pass

    print("  Press CTRL+C to stop\n")

    # Launch Uvicorn
    uvicorn.run(
        "src.api:app",
        host=args.host,
        port=args.port,
        workers=worker_count if not reload else None,
        reload=reload,
        log_level="info",
        # EPYC NUMA-aware: loop=uvloop if available for better throughput
    )


if __name__ == "__main__":
    main()
