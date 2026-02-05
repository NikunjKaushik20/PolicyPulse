# Setup Guide

This document provides step-by-step instructions for setting up PolicyPulse on a fresh machine.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | 3.12 works, 3.10 untested |
| pip | Latest | `python -m pip install --upgrade pip` |
| RAM | 4GB min | 8GB recommended for embedding model |
| Disk | 2GB | For dependencies and ChromaDB data |
| OS | Windows/Linux/macOS | Tested on Windows 11, Ubuntu 22.04 |

**Optional** (for enhanced features):
- Tesseract OCR installed (for image processing)
- Internet connection (for translation/TTS APIs)

---

## Quick Start (Windows)

```batch
# Clone repository
git clone https://github.com/your-repo/PolicyPulse.git
cd PolicyPulse

# Run automated setup
setup.bat
```

The setup script will:
1. Install Python dependencies
2. Create `.env` file from template
3. Initialize ChromaDB
4. Ingest policy data (~2 minutes)

After setup:
```batch
python start.py
```

Open browser: http://localhost:8000

---

## Quick Start (Linux/macOS)

```bash
# Clone repository
git clone https://github.com/your-repo/PolicyPulse.git
cd PolicyPulse

# Run automated setup
chmod +x setup.sh
./setup.sh
```

After setup:
```bash
python start.py
```

---

## Manual Setup

If the automated scripts don't work, follow these steps:

### Step 1: Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Expected packages:
- fastapi, uvicorn (API server)
- chromadb, sentence-transformers (vector storage)
- torch (ML backend)
- Pillow, pytesseract (image processing)
- deep-translator, gTTS (translation/TTS)
- streamlit (UI)

**Common issue**: NumPy version conflict with ChromaDB
```bash
pip install "numpy<2.0,>=1.26.0" --upgrade --no-deps
```

### Step 3: Create Environment File

```bash
# Copy template
cp .env.example .env
```

Edit `.env` to add API keys (all optional):
```
GOOGLE_CLOUD_TRANSLATE_KEY=your_key_here
GEMINI_API_KEY=your_key_here
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
```

**System works fully without any API keys.** Keys enable:
- Google Translate: Better translation quality
- Gemini: Enhanced answer generation (unused in current version)
- Twilio: SMS integration (planned feature)

### Step 4: Initialize Database

```bash
# Create ChromaDB directory
mkdir chromadb_data

# Test ChromaDB initialization
python -c "from src.chromadb_setup import get_client; get_client(); print('OK')"
```

Expected output:
```
ChromaDB client initialized at ./chromadb_data
OK
```

### Step 5: Ingest Policy Data

```bash
python cli.py ingest-all
```

Expected output:
```
📦 Ingesting policy data...
✅ NREGA budgets: 63 chunks ingested
✅ NREGA news: 47 chunks ingested
✅ NREGA temporal: 21 chunks ingested
✅ RTI budgets: 54 chunks ingested
...
🎉 Ingestion complete! Total ingested: 847 chunks
```

This takes 1-3 minutes depending on hardware.

### Step 6: Start Server

```bash
python start.py
```

Expected output:
```
==================================================
PolicyPulse - Community Impact Platform
==================================================

Starting FastAPI server...
API documentation: http://localhost:8000/docs
Main UI: http://localhost:8000

ℹ️  Running in basic mode (no API keys configured)

INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## Verifying Installation

### Test API Health

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "healthy", "service": "PolicyPulse API", "version": "2.0"}
```

### Test Query Endpoint

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "What is NREGA?"}'
```

Expected: JSON response with `final_answer`, `retrieved_points`, `confidence_score`

### Test Streamlit UI

In a separate terminal:
```bash
streamlit run app.py
```

Opens browser at http://localhost:8501

---

## Common Setup Issues

### Issue: `ModuleNotFoundError: No module named 'src'`

**Cause**: Running from wrong directory

**Fix**: Ensure you're in the PolicyPulse root directory
```bash
cd PolicyPulse
python start.py
```

### Issue: `torch` installation fails

**Cause**: PyTorch version incompatible with system

**Fix**: Install CPU-only version
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue: ChromaDB `no such column: collections.topic`

**Cause**: Corrupted database from previous version

**Fix**: Reset database
```bash
# Windows
fix_chromadb.bat

# Or manually
rmdir /s /q chromadb_data
python cli.py ingest-all
```

### Issue: OCR not working (images)

**Cause**: Tesseract not installed

**Fix (Windows)**:
1. Download installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Install to `C:\Program Files\Tesseract-OCR`
3. Add to PATH

**Fix (Linux)**:
```bash
sudo apt install tesseract-ocr
```

### Issue: `SpeechRecognition` import error

**Cause**: Missing dependency

**Fix**:
```bash
pip install SpeechRecognition
pip install pyaudio  # For audio input (optional)
```

### Issue: Port 8000 already in use

**Cause**: Another process using the port

**Fix**: Kill existing process or use different port
```bash
# Find process
netstat -ano | findstr :8000

# Or start on different port
uvicorn src.api:app --port 8001
```

---

## Running Evaluation

```bash
python run_evaluation.py --policies all --test-endpoints
```

Options:
- `--policies NREGA RTI`: Evaluate specific policies
- `--test-endpoints`: Test API availability
- `--test-drift`: Test drift detection
- `--output-dir ./results`: Custom output directory

Output files:
- `evaluation_YYYYMMDD_HHMMSS.json`: Detailed results
- `evaluation_summary_YYYYMMDD_HHMMSS.csv`: Per-policy summary
- `evaluation_report_YYYYMMDD_HHMMSS.html`: Visual report

---

## Docker (Alternative)

A Dockerfile is included but not required:

```bash
docker build -t policypulse .
docker run -p 8000:8000 policypulse
```

Note: Docker image is larger (~3GB) due to PyTorch.

---

## Data Directory Structure

```
Data/
├── nrega_budgets.csv      # Budget allocations by year
├── nrega_news.csv         # News headlines and summaries
├── nrega_temporal.txt     # Year-by-year policy evolution
├── rti_budgets.csv
├── rti_news.csv
├── rti_temporal.txt
└── ... (10 policies × 3 file types)
```

**CSV format for budgets**:
```csv
year,allocated_crores,spent_crores,focus_area
2020,40100,31005,Water conservation
```

**CSV format for news**:
```csv
year,headline,summary,source,sentiment
2020,NREGA demand surges,Workers return to villages,Economic Times,positive
```

**Text format for temporal**:
```
Year 2020:
The COVID-19 pandemic triggered unprecedented surge in NREGA demand...

Year 2021:
Budget allocation reached unprecedented Rs 73,000 crore...
```

---

## Adding New Policies

1. Create data files in `Data/`:
   - `{policyname}_budgets.csv`
   - `{policyname}_news.csv`
   - `{policyname}_temporal.txt`

2. Add mapping in `cli.py`:
```python
POLICY_MAPPINGS = {
    ...
    'newpolicy': 'NEW-POLICY',
}
```

3. Add eligibility rules in `src/eligibility.py` (optional)

4. Re-run ingestion:
```bash
python cli.py reset-db
python cli.py ingest-all
```

---

## Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `CHROMADB_DIR` | No | `./chromadb_data` | Vector store path |
| `GOOGLE_CLOUD_TRANSLATE_KEY` | No | None | Enhanced translation |
| `GEMINI_API_KEY` | No | None | LLM features (future) |
| `TWILIO_ACCOUNT_SID` | No | None | SMS integration |
| `TWILIO_AUTH_TOKEN` | No | None | SMS integration |

---

## Troubleshooting Checklist

1. ✅ Python 3.11+ installed
2. ✅ Virtual environment activated
3. ✅ All dependencies installed (`pip install -r requirements.txt`)
4. ✅ `.env` file exists (copy from `.env.example`)
5. ✅ ChromaDB initialized (`chromadb_data/` exists)
6. ✅ Policy data ingested (`python cli.py ingest-all`)
7. ✅ Server running (`python start.py`)
8. ✅ No port conflicts on 8000

If still failing, run with debug logging:
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('start.py').read())"
```
