# PolicyPulse Setup Guide

Complete setup instructions for running PolicyPulse locally. Tested on Windows 10/11, Ubuntu 22.04, and macOS Ventura.

---

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.11 | `python --version` |
| pip | 21.0+ | `pip --version` |
| Git | Any | `git --version` |
| Tesseract (optional) | 4.0+ | `tesseract --version` |

**Tesseract** is only needed for document OCR features. Core search works without it.

---

## Quick Setup (Recommended)

### Windows

```batch
git clone https://github.com/NikunjKaushik20/PolicyPulse.git
cd PolicyPulse
./setup.bat
```

### Linux / macOS

```bash
git clone https://github.com/NikunjKaushik20/PolicyPulse.git
cd PolicyPulse
chmod +x setup.sh
./setup.sh
```

The setup script performs these steps automatically:
1. Creates Python virtual environment
2. Installs dependencies from `requirements.txt`
3. Creates `.env` from `.env.example`
4. Initializes ChromaDB directory
5. Ingests all policy data

**Total time:** 3-5 minutes (first run downloads ~400MB of model weights)

---

## Manual Setup (Step-by-Step)

If the automated script fails, follow these steps:

### Step 1: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Known issue:** NumPy 2.0 breaks ChromaDB. Force compatible version:
```bash
pip install "numpy<2.0,>=1.26.0" --upgrade --no-deps
```

### Step 3: Create Environment File

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

Edit `.env` if you want enhanced features (all optional):
```
# Optional API Keys - System works WITHOUT these

# Google Cloud Translation (FREE: 500K chars/month)
GOOGLE_CLOUD_TRANSLATE_KEY=

# Gemini API for enhanced answers (FREE: 60 req/min)
GEMINI_API_KEY=

# Twilio for SMS bot (not implemented in current version)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# ChromaDB storage location
CHROMADB_DIR=./chromadb_data
```

### Step 4: Initialize ChromaDB

```bash
# Windows
python -c "from src.chromadb_setup import get_client; get_client(); print('ChromaDB initialized!')"

# Linux/macOS
python3 -c "from src.chromadb_setup import get_client; get_client(); print('ChromaDB initialized!')"
```

Expected output:
```
ChromaDB client initialized at ./chromadb_data
ChromaDB initialized!
```

### Step 5: Ingest Policy Data

```bash
python cli.py ingest-all
```

This reads all CSV files from `Data/` directory and indexes them in ChromaDB.

Expected output:
```
[1/3] Ingesting text data...
Ingested 45 text documents
[2/3] Ingesting budget data...
Ingested 180 budget entries
[3/3] Ingesting news data...
Ingested 89 news articles

Total: 847 documents ingested
```

---

## Running the Application

### Production Mode (Recommended)

Use this for demos, evaluation, or when you're not editing frontend code.

```bash
python start.py
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     ChromaDB initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Access:** http://localhost:8000

The backend serves the pre-built React frontend from `static/` (copied from `frontend/dist/`).

---

### Development Mode

Use this when editing frontend code—changes appear instantly without rebuilding.

**Terminal 1: Start Backend**
```bash
python start.py
# Backend runs on http://localhost:8000
```

**Terminal 2: Start Frontend Dev Server**
```bash
cd frontend
npm install      # first time only
npm run dev -- --host
# Frontend runs on http://localhost:5173
```

**Access:** http://localhost:5173

The Vite dev server:
- Hot reloads React code changes instantly
- Proxies `/query`, `/auth/*`, `/history` etc. to the backend on :8000
- Shows compilation errors in the browser

---

### Rebuilding Frontend for Production

After making frontend changes, rebuild for production use:

```bash
cd frontend
npm run build
```

This generates `frontend/dist/` which `start.py` serves automatically.

---

## Verifying the Installation

### Test 1: Health Check

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "healthy"}
```

### Test 2: Simple Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "What is NREGA?"}'
```

Expected response contains:
- `final_answer`: Description of NREGA
- `confidence_score`: Value between 0-1
- `sources`: List of retrieved documents

### Test 3: Check ChromaDB Contents

```bash
python -c "from src.chromadb_setup import get_collection_info; import json; print(json.dumps(get_collection_info(), indent=2))"
```

Expected:
```json
{
  "total_points": 847,
  "collection_name": "policy_data",
  "policy_breakdown": {
    "NREGA": 131,
    "RTI": 108,
    "PM-KISAN": 54,
    ...
  }
}
```

---

## Running Evaluation

To run the full evaluation suite:

```bash
python run_evaluation.py
```

This executes 60+ test queries across 10 policies and generates:
- `evaluation_results/evaluation_*.json` - Detailed results
- `evaluation_results/evaluation_summary.csv` - Summary metrics

---

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'chromadb'`

**Cause:** Virtual environment not activated.

**Fix:**
```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### Issue: `numpy.core.multiarray failed to import`

**Cause:** NumPy 2.0 incompatibility with ChromaDB.

**Fix:**
```bash
pip install "numpy<2.0,>=1.26.0" --upgrade --no-deps
```

### Issue: `RuntimeError: Your system has an unsupported version of sqlite3`

**Cause:** ChromaDB requires SQLite 3.35+. Common on older Linux systems.

**Fix:**
```bash
pip install pysqlite3-binary
```

Then add to top of `src/chromadb_setup.py`:
```python
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
```

### Issue: `OSError: [Errno 98] Address already in use`

**Cause:** Port 8000 is occupied.

**Fix:**
```bash
# Find process on port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/macOS
lsof -i :8000
kill -9 <pid>
```

Or use different port:
```bash
uvicorn src.api:app --port 8001
```

### Issue: `pytesseract.TesseractNotFoundError`

**Cause:** Tesseract not installed (needed for OCR features only).

**Fix (Windows):**
Download from: https://github.com/UB-Mannheim/tesseract/wiki
Add to PATH during installation.

**Fix (Linux):**
```bash
sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam tesseract-ocr-tel
```

**Fix (macOS):**
```bash
brew install tesseract tesseract-lang
```

### Issue: ChromaDB corruption

**Symptoms:** `sqlite3.DatabaseError` or queries returning empty results.

**Fix:**
```bash
# Delete and reingest
rm -rf chromadb_data/
python cli.py ingest-all
```

---

## Optional: Tesseract Language Packs

For OCR in Indian languages:

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr-hin tesseract-ocr-tam tesseract-ocr-tel tesseract-ocr-ben

# macOS
brew install tesseract-lang
```

---

## Optional: Building Frontend (Development)

The repository includes pre-built frontend files. To rebuild:

```bash
cd frontend
npm install
npm run build
```

This generates `frontend/dist/` which is served by FastAPI.

For development with hot reload:
```bash
cd frontend
npm run dev
```

Then access frontend at http://localhost:5173 (proxies API calls to :8000).

---

## Environment Variables Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHROMADB_DIR` | `./chromadb_data` | Vector database location |
| `GOOGLE_CLOUD_TRANSLATE_KEY` | (none) | Enhanced translation (optional) |
| `GEMINI_API_KEY` | (none) | LLM-enhanced answers (optional) |
| `TWILIO_ACCOUNT_SID` | (none) | SMS bot (not implemented) |
| `TWILIO_AUTH_TOKEN` | (none) | SMS bot (not implemented) |
| `TWILIO_PHONE_NUMBER` | (none) | SMS bot (not implemented) |

**Note:** All API keys are optional. Core functionality works without them.

---

## File Sizes After Setup

| Directory | Size | Contents |
|-----------|------|----------|
| `venv/` | ~1.5 GB | Python packages + models |
| `chromadb_data/` | ~50 MB | Vector database |
| `Data/` | ~2 MB | Source CSV files |
| `frontend/dist/` | ~5 MB | Built React app |

Total disk usage: **~1.6 GB**

---

## Next Steps

After successful setup:

1. **Start exploring:** Open http://localhost:8000 and try queries
2. **Run evaluation:** `python run_evaluation.py`
3. **Read architecture:** See `architecture.md` for system design
4. **Try examples:** See `examples.md` for query patterns
