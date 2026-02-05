# Setup Guide

This is a step-by-step guide to get PolicyPulse running on your machine. Tested on Windows 11 and Ubuntu 22.04. Should work on macOS but untested.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.11 or 3.12 (3.10 might work but untested) |
| pip | Latest version (`python -m pip install --upgrade pip`) |
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
git clone <your-repo-url>
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
git clone <your-repo-url>
cd PolicyPulse
chmod +x setup.sh
./setup.sh
```

After setup:
```bash
python start.py
```

---

## Manual Setup (If Scripts Fail)

### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd PolicyPulse
```

### Step 2: Check Python Version

```bash
python --version
```

Should show `Python 3.11.x` or `3.12.x`. If you have Python 3.10, it might work but we haven't tested.

### Step 3: Create Virtual Environment (Recommended)

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

This installs 21 packages:
- fastapi, uvicorn (API server)
- chromadb, sentence-transformers (vector search)
- torch (ML backend)
- Pillow, pytesseract (OCR)
- deep-translator, gTTS (translation/TTS)
- langdetect (language detection)
- pandas, numpy (data handling)

**Expected output:** Should complete in 2-5 minutes depending on your internet speed. PyTorch is the largest download (~800MB).

**Common issue:** NumPy version conflict

If you see errors about NumPy compatibility with ChromaDB:
```bash
pip install "numpy<2.0,>=1.26.0" --upgrade --force-reinstall
```

### Step 5: Configure Environment Variables

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

**The system works fully without any API keys.** Speech recognition, translation, and TTS use free tiers of Google services.

### Step 6: Initialize ChromaDB

Test that ChromaDB can initialize:

```bash
python -c "from src.chromadb_setup import get_client; get_client(); print('ChromaDB OK')"
```

Expected output:
```
ChromaDB client initialized at ./chromadb_data
ChromaDB OK
```

If you see errors, likely causes:
1. Python version too old (need 3.11+)
2. NumPy version incompatible
3. Missing directory permissions

### Step 7: Ingest Policy Data

This is the critical step. We load 10 policies × 3 modalities into ChromaDB.

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
✅ RTI news: 41 chunks ingested
✅ RTI temporal: 13 chunks ingested

...
(continues for 10 policies)

🎉 Ingestion complete!
Total chunks: 847
Time taken: 2m 14s
```

**This takes 1-3 minutes** depending on your CPU. The sentence-transformer model is downloaded on first run (~100MB).

**What's happening:**
- Reads CSVs and text files from `Data/` directory
- Splits into chunks (200 characters each for structured data, by year for temporal data)
- Generates embeddings (384-dim vectors)
- Stores in ChromaDB with metadata

**If ingestion fails midway:**
```bash
# Reset database and try again
python cli.py reset-db
python cli.py ingest-all
```

### Step 8: Start Server

```bash
python start.py
```

Expected output:
```
==================================================
PolicyPulse - Government Policy Search System
==================================================

✅ ChromaDB initialized (847 chunks loaded)
✅ Starting FastAPI server on port 8000...

🌐 API documentation: http://localhost:8000/docs
🌐 Main UI: http://localhost:8000

ℹ️  Running in basic mode (no API keys configured)

INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Server is now running. Open http://localhost:8000 in your browser.

---

## Verifying Installation

### Test 1: API Health Check

In a new terminal (keep server running):

```bash
curl http://localhost:8000/health
```

Expected response:
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
  -d '{"policy_id": "NREGA", "question": "What is NREGA?", "top_k": 3}'
```

Should return JSON with `final_answer`, `retrieved_points`, `confidence_score`.

### Test 3: Streamlit UI (Alternative Interface)

In a separate terminal:

```bash
streamlit run app.py
```

Opens browser at http://localhost:8501. This is a more user-friendly interface than the raw API.

---

## Common Setup Issues

### Issue: `ModuleNotFoundError: No module named 'src'`

**Cause:** Running Python from wrong directory.

**Fix:**
```bash
cd PolicyPulse  # Make sure you're in the repo root
python start.py
```

### Issue: `torch` installation fails on Windows

**Cause:** PyTorch sometimes has issues with pip on Windows.

**Fix:** Install CPU-only version explicitly:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue: ChromaDB error: `no such column: collections.topic`

**Cause:** Corrupted database from a failed ingestion or version mismatch.

**Fix (Windows):**
```batch
fix_chromadb.bat
```

**Fix (Linux/macOS):**
```bash
rm -rf chromadb_data/
python cli.py ingest-all
```

### Issue: OCR not working (images)

**Cause:** Tesseract not installed.

**Fix (Windows):**
1. Download installer: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to `C:\Program Files\Tesseract-OCR`
3. Add to PATH: System Properties → Environment Variables → Path → Add `C:\Program Files\Tesseract-OCR`

**Fix (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install tesseract-ocr
```

**Fix (macOS):**
```bash
brew install tesseract
```

Test OCR:
```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

### Issue: `SpeechRecognition` fails to transcribe

**Cause:** No internet connection (Google Speech API needs internet).

**Fix:** This is expected. Speech recognition requires internet currently. Core text search works offline.

Alternative: Use text input instead of voice.

### Issue: Port 8000 already in use

**Cause:** Previous server instance didn't shut down cleanly.

**Fix (Windows):**
```batch
# Find process using port 8000
netstat -ano | findstr :8000
# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Fix (Linux/macOS):**
```bash
# Find process
lsof -i :8000
# Kill process
kill -9 <PID>
```

Or start on a different port:
```bash
uvicorn src.api:app --port 8001
```

### Issue: `ImportError: cannot import name 'SentenceTransformer'`

**Cause:** sentence-transformers installation failed.

**Fix:**
```bash
pip uninstall sentence-transformers
pip install sentence-transformers==2.7.0
```

### Issue: Import takes forever / system freezes

**Cause:** Low RAM (4GB). Embedding model + ChromaDB + PyTorch competing for memory.

**Fix:**
1. Close other applications
2. Ingest in smaller batches:
```bash
# Instead of ingest-all, do one policy at a time
python cli.py ingest-policy NREGA
python cli.py ingest-policy RTI
# etc.
```

---

## Running Evaluation

Test the system with our evaluation suite:

```bash
python run_evaluation.py --policies NREGA RTI --test-endpoints
```

Arguments:
- `--policies [LIST]`: Which policies to test (default: NREGA, RTI)
- `--test-endpoints`: Verify API is responding
- `--test-drift`: Test drift detection
- `--output-dir ./results`: Where to save results

Expected output:
```
🧪 PolicyPulse Evaluation Suite

Testing NREGA (10 queries)...
✓ Query 1/10: What was the original intent of NREGA in 2005? [0.557]
✓ Query 2/10: How did MGNREGA change in 2009? [0.497]
...

Summary:
- Total queries: 20
- Average similarity: 0.575
- Year accuracy: 100%
- Modality accuracy: 60%

Results saved to: evaluation_results/
```

This runs our 20-query test set and compares against expected results.

---

## Data Directory Structure

The `Data/` directory contains policy data:

```
Data/
├── nrega_budgets.csv
├── nrega_news.csv
├── nrega_temporal.txt
├── rti_budgets.csv
├── rti_news.csv
├── rti_temporal.txt
└── ... (10 policies × 3 files each)
```

**Budget CSV format:**
```csv
year,allocated_crores,spent_crores,focus_area
2020,60100,58432,Infrastructure development
2021,73000,71234,Wage arrears clearance
```

**News CSV format:**
```csv
year,headline,summary,source,sentiment
2020,NREGA wages increased,Government raises daily wage to Rs 202,The Hindu,positive
```

**Temporal TXT format:**
```
Year 2020:
The National Rural Employment Guarantee Act saw unprecedented demand during COVID-19...

Year 2021:
Budget allocation reached Rs 73,000 crore, focusing on clearing wage arrears...
```

---

## Adding New Policies

If you want to add an 11th policy (e.g., GST):

**1. Create data files in `Data/`:**
- `gst_budgets.csv`
- `gst_news.csv`
- `gst_temporal.txt`

**2. Add mapping in `cli.py`:**

Edit the `POLICY_MAPPINGS` dict:
```python
POLICY_MAPPINGS = {
    "nrega": "NREGA",
    "rti": "RTI",
    # ... existing policies
    "gst": "GST",  # Add this line
}
```

**3. (Optional) Add eligibility rules in `src/eligibility.py`:**
```python
"GST": {
    "description": "Goods and Services Tax registration",
    "rules": {
        "occupation": ["business_owner", "trader"],
        "annual_turnover": 4000000  # ₹40L threshold
    }
}
```

**4. Re-ingest:**
```bash
python cli.py reset-db
python cli.py ingest-all
```

---

## Docker (Alternative Deployment)

A Dockerfile is included but not required for development:

```bash
docker build -t policypulse .
docker run -p 8000:8000 policypulse
```

**Note:** Docker image is large (~3GB) due to PyTorch. For hackathon demo, we recommend native Python setup.

---

## Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `CHROMADB_DIR` | No | `./chromadb_data` | Where ChromaDB stores data |
| `GOOGLE_CLOUD_TRANSLATE_KEY` | No | None | Better translation via Cloud Translate API |
| `GEMINI_API_KEY` | No | None | LLM features (not used currently) |
| `TWILIO_ACCOUNT_SID` | No | None | SMS interface (planned) |
| `TWILIO_AUTH_TOKEN` | No | None | SMS authentication |

---

## Troubleshooting Checklist

If something isn't working, go through this:

1. ✅ Python 3.11+ installed (`python --version`)
2. ✅ Virtual environment activated (`which python` should point to `venv/`)
3. ✅ All dependencies installed (`pip list | grep chromadb`)
4. ✅ `.env` file exists (copy from `.env.example`)
5. ✅ ChromaDB initialized (`ls chromadb_data/` should show files)
6. ✅ Policy data ingested (`python cli.py stats` should show 847 chunks)
7. ✅ Server running on port 8000 (`curl http://localhost:8000/health`)
8. ✅ No port conflicts (`netstat -an | grep 8000`)

If all checks pass but still failing, run with debug logging:

```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG); import start"
```

Look for error messages in the output.

---

## Performance Expectations

On a typical development machine (Intel i5, 8GB RAM, SSD):

| Operation | Time |
|-----------|------|
| Initial setup (deps + ingest) | 5-7 minutes |
| Server startup | 3-5 seconds |
| Simple query (text) | 150-200ms |
| Drift analysis | 800ms-1.2s |
| Query with translation | 400-500ms |
| Query with TTS | 600-800ms |
| Image OCR + query | 2-3 seconds |

If you're seeing significantly slower times:
- Check RAM usage (might be swapping to disk)
- Check internet connection (translation/TTS add latency)
- Check disk I/O (SSD recommended)

---

## Next Steps After Setup

1. **Try the demo:** Open http://localhost:8000 and ask "What is NREGA?"
2. **Test multimodal:** Upload an image with text and see OCR in action
3. **Check drift:** Go to Drift tab, select NREGA, analyze temporal drift
4. **Run evaluation:** `python run_evaluation.py` to see test results
5. **Explore API docs:** http://localhost:8000/docs for full API reference

---

This setup should work out of the box on a fresh machine. We tested it on:
- Windows 11 (Python 3.11)
- Ubuntu 22.04 (Python 3.11)
- WSL2 Ubuntu (Python 3.12)

If you encounter issues not covered here, check the GitHub issues or add your own.
