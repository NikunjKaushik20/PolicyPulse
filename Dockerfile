# ─────────────────────────────────────────────────────────────────────────────
# PolicyPulse — AMD Instinct / EPYC Docker Image
# ─────────────────────────────────────────────────────────────────────────────
# Base: rocm/pytorch — AMD's official ROCm-enabled PyTorch image
# GPU target: AMD Instinct MI250X / MI300X (gfx90a / gfx940)
# CPU target: AMD EPYC (any generation)
#
# Build:
#   docker build -t policypulse-amd .
#
# Run (AMD GPU):
#   docker run --device=/dev/kfd --device=/dev/dri \
#     --group-add video --group-add render \
#     -p 8000:8000 policypulse-amd
#
# Run (EPYC CPU-only):
#   docker run --cpus=$(nproc) -p 8000:8000 policypulse-amd --dev
# ─────────────────────────────────────────────────────────────────────────────

# Use AMD's official ROCm PyTorch base image
# rocm/pytorch ships torch built with HIP/ROCm — no CUDA needed
ARG ROCM_VERSION=6.1
ARG TORCH_VERSION=2.2

FROM rocm/pytorch:rocm${ROCM_VERSION}_ubuntu22.04_py3.10_pytorch_${TORCH_VERSION}

LABEL maintainer="PolicyPulse Team" \
      description="AMD EPYC + Instinct optimised PolicyPulse" \
      rocm.version="${ROCM_VERSION}" \
      torch.version="${TORCH_VERSION}"

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-hin \
      tesseract-ocr-tam \
      tesseract-ocr-tel \
      tesseract-ocr-ben \
      tesseract-ocr-mar \
      ffmpeg \
      libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ── Python environment ─────────────────────────────────────────────────────────
WORKDIR /app

COPY requirements.txt requirements_amd.txt* ./

# Install Python deps (torch is already installed in the base image — skip it)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      fastapi==0.109.0 \
      uvicorn==0.27.0 \
      pydantic==2.5.3 \
      slowapi==0.1.9 \
      "chromadb>=1.4.1" \
      "sentence-transformers==2.7.0" \
      "transformers==4.36.2" \
      pandas==2.1.4 \
      "numpy>=1.26.0,<2.0" \
      Pillow==10.2.0 \
      pytesseract==0.3.10 \
      python-multipart==0.0.6 \
      deep-translator==1.11.4 \
      gTTS==2.5.0 \
      google-generativeai==0.3.2 \
      google-cloud-translate==3.14.0 \
      twilio==8.11.1 \
      python-dotenv==1.0.0 \
      langdetect==1.0.9 \
      "pymongo>=4.6.1" \
      "python-jose[cryptography]" \
      "passlib[bcrypt]" \
      multipart \
      "librosa>=0.10.1" \
      "fastembed>=0.2.0" \
      "qdrant-client>=1.7.0" \
      "tinydb>=4.8.0" \
      networkx \
      soundfile

# ── AMD ROCm environment variables ────────────────────────────────────────────
# These are set at container level — individual workers inherit them.
ENV HSA_ENABLE_SDMA=0 \
    PYTORCH_HIP_ALLOC_CONF=max_split_size_mb:512 \
    TOKENIZERS_PARALLELISM=false \
    # GOMP: bind OpenMP threads to EPYC cores for NUMA locality
    GOMP_CPU_AFFINITY="0-95" \
    # ROCm logging — set to 4 (info) for production, 7 (debug) for diagnostics
    AMD_LOG_LEVEL=4 \
    # EPYC threading — overridden at runtime via start_amd.py
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4

# ── Copy application ───────────────────────────────────────────────────────────
COPY . .

# ── Expose port ────────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Healthcheck ────────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# ── Default command: AMD-optimized multi-worker server ─────────────────────────
# start_amd.py auto-detects EPYC core count and sizes workers accordingly.
CMD ["python", "start_amd.py"]
