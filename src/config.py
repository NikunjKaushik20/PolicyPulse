"""
PolicyPulse Configuration — AMD-Optimized
==========================================
Device priority order:
  1. AMD Instinct GPU via ROCm  (torch.version.hip is set)
  2. Any CUDA-compatible GPU    (fallback)
  3. AMD EPYC CPU               (always available)

All hardware constants are derived from amd_utils so they stay
consistent across every module that imports config.
"""

# ── AMD device selection ──────────────────────────────────────────────────────
from .amd_utils import (
    detect_amd_device,
    optimal_batch_size,
    optimal_worker_count,
    get_epyc_core_count,
    get_gpu_memory_gb,
)

_DEVICE_STR, AMD_BACKEND_LABEL = detect_amd_device()

# torch.device string used by all model loaders ("cuda" for ROCm/NVIDIA, "cpu")
DEVICE = _DEVICE_STR

# Human-readable AMD backend info (logged at startup + /health endpoint)
# e.g. "AMD Instinct (ROCm) — gfx1100" or "CPU — 96 logical cores"
BACKEND_LABEL = AMD_BACKEND_LABEL

# ── Embedding models ──────────────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SENTIMENT_MODEL  = "cardiffnlp/twitter-roberta-base-sentiment-latest"
EMBEDDING_DIM    = 384          # all-MiniLM-L6-v2 output dimension

# ── AMD-tuned batch / worker sizes ───────────────────────────────────────────
# Automatically scale with available GPU VRAM (MI300X → 256, CPU → 16)
EMBED_BATCH_SIZE  = optimal_batch_size("text")
IMAGE_BATCH_SIZE  = optimal_batch_size("image")
AUDIO_BATCH_SIZE  = optimal_batch_size("audio")

# EPYC core-aware thread pool sizes
OCR_WORKER_COUNT  = optimal_worker_count("ocr")   # Tesseract parallelism
IO_WORKER_COUNT   = optimal_worker_count("io")    # DB / network I/O
CPU_CORE_COUNT    = get_epyc_core_count()
GPU_MEMORY_GB     = get_gpu_memory_gb()

# ── ChromaDB (Vector Store) ───────────────────────────────────────────────────
CHROMA_PERSIST_DIR = "chromadb_data"
COLLECTION_NAME    = "policy_documents"

# ── Memory / decay parameters ─────────────────────────────────────────────────
DECAY_RATE          = 0.85
REINFORCEMENT_RATE  = 1.02
TIME_DECAY_MONTHS   = 6

# ── Drift detection thresholds ────────────────────────────────────────────────
DRIFT_HIGH   = 0.5
DRIFT_MEDIUM = 0.3
DRIFT_LOW    = 0.1

# ── Data paths ────────────────────────────────────────────────────────────────
DATA_DIR    = "data"
SAMPLE_TEXT   = f"{DATA_DIR}/sample_nrega_2005.txt"
SAMPLE_BUDGET = f"{DATA_DIR}/sample_budgets.csv"
SAMPLE_NEWS   = f"{DATA_DIR}/sample_news.csv"
