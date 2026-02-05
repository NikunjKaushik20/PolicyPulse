# Setup Guide

Step-by-step guide to get PolicyPulse running on your machine. Tested on Windows 11, Ubuntu 22.04, and WSL2. A judge should be able to run this at 2 AM on a fresh machine.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.11 or 3.12 (3.10 untested) |
| pip | Latest version |
| RAM | 4GB minimum, 8GB recommended |
| Disk | 2GB for dependencies + data |
| OS | Windows, Linux, or macOS |

**Optional (for full features):**
- Tesseract OCR (for image processing)
- Internet connection (for translation/TTS—core search works offline)

---

## Quick Start (Automated)

### Windows

```batch
git clone https://github.com/NikunjKaushik/PolicyPulse.git
cd PolicyPulse
setup.bat
```

The script will:
1. Check Python version
2. Install dependencies from `requirements.txt`
3. Copy `.env.example` to `.env`
4. Initialize ChromaDB
5. Ingest policy data (~2 minutes)

After setup completes:
```batch
python start.py
```

Open browser to http://localhost:8000

### Linux/macOS

```bash
git clone https://github.com/NikunjKaushik/PolicyPulse.git
cd PolicyPulse
chmod +x setup.sh
./setup.sh
python start.py
```

---

## Manual Setup (If Scripts Fail)

### Step 1: Clone Repository

```bash
git clone https://github.com/NikunjKaushik/PolicyPulse.git
cd PolicyPulse
```

### Step 2: Check Python Version

```bash
python --version
```

Expected: `Python 3.11.x` or `3.12.x`

### Step 3: Create Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows:**
```batch
venv\Scripts\activate
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected time:** 2-5 minutes (PyTorch is ~800MB download)

**Installs:**
- fastapi, uvicorn (API server)
- chromadb, sentence-transformers (vector search)
- torch (ML backend)
- Pillow, pytesseract (OCR)
- deep-translator, gTTS (translation/TTS)
- langdetect (language detection)
- pandas, numpy (data handling)

### Step 5: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` if you have API keys (ALL OPTIONAL):

```
# Optional: Better translation quality
GOOGLE_CLOUD_TRANSLATE_KEY=your_key_here

# Optional: LLM features (not currently used)
GEMINI_API_KEY=your_key_here

# Optional: SMS interface (planned)
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
```

**The system works fully without any API keys.** Speech recognition, translation, and TTS use free tiers.

### Step 6: Test ChromaDB

```bash
python -c "from src.chromadb_setup import get_client; get_client(); print('ChromaDB OK')"
```

Expected:
```
ChromaDB client initialized at ./chromadb_data
ChromaDB OK
```

### Step 7: Ingest Policy Data

This is critical. Loads 10 policies × 3 modalities into ChromaDB.

```bash
python cli.py ingest-all
```

Expected output:
```
📦 Starting bulk ingestion for all policies...

Processing NREGA...
✅ NREGA budgets: 63 chunks ingested
✅ NREGA news: 47 chunks ingested
✅ NREGA temporal: 21 chunks ingested

Processing RTI...
✅ RTI budgets: 54 chunks ingested
...

🎉 Ingestion complete!
Total chunks: 847
Time taken: 2m 14s
```

**Takes 1-3 minutes.** Sentence-transformer model downloads on first run (~100MB).

### Step 8: Start Server

```bash
python start.py
```

Expected:
```
==================================================
PolicyPulse - Government Policy Search System
==================================================

✅ ChromaDB initialized (847 chunks loaded)
✅ Starting FastAPI server on port 8000...

🌐 API documentation: http://localhost:8000/docs
🌐 Main UI: http://localhost:8000

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Open http://localhost:8000 in browser.

---

## Verification

### Test 1: Health Check

```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "service": "PolicyPulse API",
  "version": "2.0",
  "total_points": 847
}
```

### Test 2: Query Endpoint

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "What is NREGA?", "top_k": 3}'
```

Should return JSON with `final_answer`, `retrieved_points`, `confidence_score`.

### Test 3: Streamlit UI

In a separate terminal:
```bash
streamlit run app.py
```

Opens at http://localhost:8501 (alternative interface).

---

## Common Issues

### `ModuleNotFoundError: No module named 'src'`

**Cause:** Running Python from wrong directory.

**Fix:**
```bash
cd PolicyPulse  # Must be in repo root
python start.py
```

### `torch` installation fails (Windows)

**Cause:** pip issues with PyTorch on Windows.

**Fix:**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### ChromaDB error: `no such column: collections.topic`

**Cause:** Corrupted database from failed ingestion.

**Fix (Windows):**
```batch
scripts\fix_chromadb.bat
```

**Fix (Linux/macOS):**
```bash
rm -rf chromadb_data/
python cli.py ingest-all
```

### NumPy version conflict

**Fix:**
```bash
pip install "numpy<2.0,>=1.26.0" --upgrade --force-reinstall
```

### OCR not working

**Cause:** Tesseract not installed.

**Windows:**
1. Download: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to `C:\Program Files\Tesseract-OCR`
3. Add to PATH

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Verify:**
```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

### Speech recognition fails

**Cause:** No internet (Google Speech API requires internet).

**Fix:** Use text input instead. Core search works offline.

### Port 8000 in use

**Windows:**
```batch
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/macOS:**
```bash
lsof -i :8000
kill -9 <PID>
```

Or use different port:
```bash
uvicorn src.api:app --port 8001
```

### Import takes forever / system freezes

**Cause:** Low RAM (4GB). Embedding model + ChromaDB competing for memory.

**Fix:**
1. Close other applications
2. Ingest one policy at a time:
```bash
python cli.py ingest-policy NREGA
python cli.py ingest-policy RTI
```

---

## Running Evaluation

```bash
python run_evaluation.py --policies NREGA RTI --test-endpoints
```

**Arguments:**
- `--policies [LIST]`: Which policies to test
- `--test-endpoints`: Verify API responding
- `--test-drift`: Test drift detection
- `--output-dir ./results`: Save location

Expected output:
```
🧪 PolicyPulse Evaluation Suite

Testing NREGA (10 queries)...
✓ Query 1/10: What was the original intent of NREGA in 2005? [0.557]
...

Summary:
- Total queries: 20
- Average similarity: 0.575
- Year accuracy: 100%
- Modality accuracy: 60%

Results saved to: evaluation_results/
```

---

## Data Files

The `Data/` directory contains policy data (223 files):

```
Data/
├── nrega_budgets.csv
├── nrega_news.csv
├── nrega_temporal.txt
├── rti_budgets.csv
...
```

**Budget CSV format:**
```csv
year,allocated_crores,spent_crores,focus_area
2020,60100,58432,Infrastructure development
```

**News CSV format:**
```csv
year,headline,summary,source,sentiment
2020,NREGA wages increased,Government raises daily wage,The Hindu,positive
```

**Temporal TXT format:**
```
Year 2020:
The National Rural Employment Guarantee Act saw unprecedented demand during COVID-19...
```

---

## Adding New Policies

To add an 11th policy (e.g., GST):

**1. Create data files:**
- `Data/gst_budgets.csv`
- `Data/gst_news.csv`
- `Data/gst_temporal.txt`

**2. Add mapping in `cli.py`:**
```python
POLICY_MAPPINGS = {
    ...
    "gst": "GST",
}
```

**3. Add eligibility rules in `src/eligibility.py`** (optional)

**4. Re-ingest:**
```bash
python cli.py reset-db
python cli.py ingest-all
```

---

## Docker (Alternative)

```bash
docker build -t policypulse .
docker run -p 8000:8000 policypulse
```

**Note:** Image is ~3GB due to PyTorch. Native Python recommended for hackathon demo.

---

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `CHROMADB_DIR` | No | `./chromadb_data` | Vector store location |
| `GOOGLE_CLOUD_TRANSLATE_KEY` | No | None | Better translation |
| `GEMINI_API_KEY` | No | None | LLM features (unused) |
| `TWILIO_ACCOUNT_SID` | No | None | SMS (planned) |

---

## Troubleshooting Checklist

If something isn't working:

1. ✅ Python 3.11+ installed (`python --version`)
2. ✅ Virtual environment activated (`which python` → `venv/`)
3. ✅ Dependencies installed (`pip list | grep chromadb`)
4. ✅ `.env` file exists
5. ✅ ChromaDB initialized (`ls chromadb_data/`)
6. ✅ Data ingested (`python cli.py stats` → 847 chunks)
7. ✅ Server running (`curl http://localhost:8000/health`)
8. ✅ No port conflicts (`netstat -an | grep 8000`)

Debug mode:
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG); import start"
```

---

## Performance Expectations

On typical development hardware (Intel i5, 8GB RAM, SSD):

| Operation | Time |
|-----------|------|
| Initial setup (deps + ingest) | 5-7 minutes |
| Server startup | 3-5 seconds |
| Simple query | 150-200ms |
| Drift analysis | 800ms-1.2s |
| Query with translation | 400-500ms |
| Query with TTS | 600-800ms |
| Image OCR + query | 2-3 seconds |

If significantly slower: check RAM usage (swapping), internet (translation lag), disk (HDD vs SSD).

---

## Post-Setup

1. **Try demo:** Open http://localhost:8000, ask "What is NREGA?"
2. **Test multimodal:** Upload image with text, see OCR
3. **Check drift:** Go to Drift tab, select NREGA, analyze
4. **Run evaluation:** `python run_evaluation.py`
5. **API docs:** http://localhost:8000/docs

---

Setup tested on:
- Windows 11 (Python 3.11)
- Ubuntu 22.04 (Python 3.11)
- WSL2 Ubuntu (Python 3.12)
- macOS Sonoma (Python 3.12, not extensively tested)
