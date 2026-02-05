# PolicyPulse

A retrieval system for querying Indian government policy data across time. Built during the AI for Community Impact hackathon to address a real problem: citizens can't easily find out which schemes they're eligible for or how policies have changed.

## The Problem We Observed

We talked to Jan Seva Kendra staff and local NGO workers during the kickoff phase. The pattern was consistent: people show up asking "can I get PM-KISAN?" or "what's the current NREGA wage?" Staff either don't know, pull up outdated PDFs, or send people to 3-4 different ministry websites.

Three specific failures we documented:
1. **Discovery**: Farmer with 1.5 hectares doesn't know PM-KISAN exists (income-eligible but unaware)
2. **Currency**: NREGA worker quoted 2022 wage rates in 2024 (₹45/day error)
3. **Comprehension**: RTI applicant couldn't parse 2019 amendment Act language

Government portals are document archives. You can download the 2020 NREGA notification PDF, but you can't ask "what changed from 2019 to 2020" and get an answer.

## What We Built

PolicyPulse ingests policy documents (text files we curated from official sources) and builds a semantic search index. You ask a question in natural language, we retrieve relevant chunks from the vector store, and synthesize an answer showing exactly which year/document it came from.

**Core loop:**
```
User query → Policy detection (keyword-based)
         → Vector search (ChromaDB + sentence-transformers)
         → Time-weighted ranking
         → Structured answer with sources
```

**Coverage:** 10 major Indian policies (NREGA, RTI, PM-KISAN, Ayushman Bharat, Swachh Bharat, Digital India, Make in India, Skill India, Smart Cities, NEP), 2005-2025 data.

**Input modalities:**
- Text queries (direct)
- Voice (Google Speech Recognition API)
- Images (pytesseract OCR for documents like Aadhaar cards)
- Video (PyAV audio extraction + transcription)

Language support: Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, English via auto-detection and deep-translator.

## What We Did *Not* Build

- **LLM answer generation**: We use retrieval + template-based synthesis, not GPT-style generation. This is intentional. Government use requires showing exactly which source document supports each claim. No hallucination risk.
- **Real-time policy scraping**: Data is ingested once at setup. We don't poll ministry websites.
- **Application submission**: We tell users what they need and link to official portals. We don't handle enrollment.
- **Comprehensive coverage**: We went deep on 10 policies rather than shallow on 100. This was a resource constraint—each policy required manually curating 20+ years of data.

## Technical Architecture

**Storage:**
- ChromaDB (embedded vector database, no Docker)
- Sentence-transformers `all-MiniLM-L6-v2` (384-dim embeddings)
- File-based policy data in `Data/` directory

**API:**
- FastAPI with rate limiting (`slowapi`)
- Pydantic validation
- 8 endpoints covering query, drift, eligibility, recommendations, translation, TTS

**Frontend:**
- Streamlit for rapid prototyping

**Why these choices:**
- ChromaDB: pure Python, persists to local directory, no separate server process
- sentence-transformers: MIT license, runs on CPU, doesn't require API keys
- Streamlit: built the UI in 2 days, adequate for demo

## Features Implemented

### 1. Semantic Policy Search
Query the vector store and get back ranked results with confidence scores. Time decay weights newer data higher (exponential decay, 0.1 coefficient per year).

Example:
```
Q: "What is NREGA wage rate?"
A: NREGA (2024): Rs 255/day average (retrieved from budget data, score 0.71)
```

### 2. Policy Drift Detection
Computes semantic distance between consecutive years to quantify policy change. We calculate the centroid (mean embedding) for each year's data, then cosine distance year-to-year.

Drift classification:
- CRITICAL (>0.70): Major overhaul
- HIGH (0.45-0.70): Significant change
- MEDIUM (0.25-0.45): Notable evolution
- LOW (0.10-0.25): Minor adjustment
- MINIMAL (<0.10): Stable

### 3. Eligibility Checker
Rule-based matching. We hardcoded eligibility criteria for 10 schemes (age, income, location, occupation, etc.). User fills out profile, system returns ranked list of applicable schemes.

Why rules, not ML: Government eligibility is explicitly documented. No training data. Rules are auditable.

### 4. Multilingual Interface
Detects input language via `langdetect`, translates to English for embedding search, translates output back via `deep-translator`. TTS via gTTS for audio output.

### 5. Multimodal Input
- **Text**: direct query
- **Voice**: speech recognition (WAV/MP3)
- **Images**: OCR via tesseract (works on Aadhaar, income certificates if print quality is decent)
- **Video**: extracts audio track, transcribes

### 6. Memory System
Time decay + access reinforcement. Recently accessed chunks get boosted. Prevents 2006 data from dominating when user asks "what's the current rate?"

## Evaluation Results

We ran tests on 20 queries (10 NREGA, 10 RTI). Ground truth was manually created by us based on known facts.

**Results (20-query test set):**
- Year accuracy: 100% (system returned correct year in top-1 result for year-specific queries)
- Modality accuracy: 60% (correct data type: budget vs temporal vs news)
- Average top-1 similarity score: 0.575

**What this means:**
If you ask "what was NREGA budget in 2020," you'll get 2020 data. But if you ask "how did NREGA change in 2009," you might get budget data when you needed temporal evolution text. This is because our keyword detection for modality isn't sophisticated—relies on terms like "budget," "allocation" for budget mode.

**Drift detection validation:**
We manually reviewed the top CRITICAL drift periods flagged by the system:
- NREGA 2019→2020: System flagged score 0.74. Actual event: COVID emergency expansion, budget doubled. **Correct.**
- RTI 2018→2019: System flagged score 0.68. Actual event: RTI Amendment Act 2019 passed. **Correct.**

8 out of 10 CRITICAL drift flags corresponded to documented policy changes.

**Latency (measured on Intel i5, 8GB RAM, SSD):**
- Simple query: ~180ms average
- Drift analysis: ~800ms (requires aggregating all yearly data)
- Translation adds ~300ms
- TTS adds ~500ms

**Limitations of our evaluation:**
1. Small test set (20 queries)
2. Ground truth created by us, not independently validated
3. No user studies—we don't know if actual citizens would find this useful
4. All tests run locally; no production load testing

## Deployment Considerations

**For a government pilot:**

1. **Data ingestion:** Currently uses curated CSVs and text files. Production would need connectors to Gazette of India, ministry press releases, official notifications. We'd need to handle PDFs, scanned documents, and inconsistent formatting.

2. **Authentication:** No auth in current system. Government deployment needs Aadhaar integration or mobile OTP.

3. **Audit trails:** We log all queries to console. Production needs structured logging with user ID, timestamp, query, response for RTI compliance.

4. **Scale:** ChromaDB is file-based, single-process. For >50 concurrent users, we'd migrate to Qdrant cluster or Pinecone. Estimated current capacity: ~10 queries/second sustained.

5. **Language coverage:** We support 10 languages. Full national rollout needs Assamese, Odia, Urdu, tribal languages.

6. **Offline mode:** Core search works offline once data is ingested. Translation and TTS require internet. For truly offline deployment (rural kiosks), would need to pre-cache common translations or use offline translation models.

## Technology Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Vector Store | ChromaDB | Embedded, no Docker, persists locally |
| Embeddings | sentence-transformers | CPU-compatible, no API costs |
| API Framework | FastAPI | Async, auto-docs, Python-native |
| Frontend | Streamlit | Rapid prototyping |
| OCR | pytesseract | Open-source, works offline |
| Translation | deep-translator | Free tier Google Translate wrapper |
| TTS | gTTS | Supports 10 languages, free |

**Why not use an LLM for answer generation?**
1. Reproducibility: same query always returns same answer
2. Transparency: we show exact source documents
3. Speed: retrieval is 180ms, LLM would add 1-3 seconds
4. Cost: no API fees

We considered Gemini integration (we have the Gemini API key setup in `.env`) but decided retrieval-only was more appropriate for government accountability.

## Known Issues and Tradeoffs

**Issue 1: Modality detection is weak**
Query "how did NREGA change" should trigger temporal mode, but often gets budget data. Keyword matching isn't robust enough. Could fix with a small classifier, but didn't have time.

**Issue 2: Policy detection defaults to NREGA**
If query is ambiguous, system picks NREGA as fallback. This biases results. Better fallback would be multi-policy search, but adds latency.

**Issue 3: OCR quality**
Handwritten documents are mostly unreadable. Works fine on printed Aadhaar cards, fails on handwritten income certificates. This is a tesseract limitation, not something we can fix without custom training.

**Issue 4: ChromaDB corruption**
Encountered SQLite corruption twice during development. Added `fix_chromadb.bat` script to reset database. For production, would need replication and backup strategy.

**Tradeoff: Embedded vs distributed vector store**
ChromaDB embedded means single-machine limit. Can only scale vertically. We chose this for hackathon simplicity—zero infrastructure, runs on laptop. Production would need Qdrant or similar.

**Tradeoff: Curated data vs scraping**
We manually curated policy data (CSVs, text files). This takes time but ensures accuracy. Automated scraping would have coverage but worse quality. We prioritized correctness over breadth.

## Quick Start

```bash
# Clone repo
git clone <repo-url>
cd PolicyPulse

# Windows
setup.bat

# Linux/macOS
chmod +x setup.sh
./setup.sh

# Start server
python start.py
# Open http://localhost:8000
```

**Requirements:**
- Python 3.11+
- 4GB RAM (8GB recommended)
- 2GB disk space

**Optional:**
- Tesseract (for OCR)
- Internet (for translation/TTS)

System works fully offline for core search functionality.

## Future Work (Realistic Extensions)

**Near-term (1-2 months):**
- Fine-tune embedding model on Indian policy text (currently uses generic English embeddings)
- Add more policies (GST, labor codes, environmental regulations)
- Caching for common queries (~80% of queries in testing were variants of "what is X" and "X budget")

**Medium-term (3-6 months):**
- DigiLocker integration for document verification
- SMS/USSD interface for feature phones (Twilio hooks are in codebase but not implemented)
- Offline embedding compression (quantization from 384-dim to 128-dim for mobile deployment)

**Research questions (if we had more time):**
- Cross-policy reasoning: "which schemes can a farmer with X income access?" (requires multi-policy joint search)
- Citation-based answer generation: LLM that shows exact span in source document
- Adversarial query testing: measure robustness to paraphrasing, typos, code-switching

## System Requirements

- Python 3.11+ (tested on 3.11, 3.12 works)
- OS: Windows 11, Ubuntu 22.04, macOS Sonoma (tested)
- RAM: 4GB minimum, 8GB recommended (embedding model loads ~400MB)
- Disk: 2GB for dependencies + ChromaDB data

## Repository Structure

```
PolicyPulse/
├── src/                    # Core modules
│   ├── api.py              # FastAPI endpoints
│   ├── chromadb_setup.py   # Vector store initialization
│   ├── reasoning.py        # Query processing and synthesis
│   ├── drift.py            # Policy evolution analysis
│   ├── memory.py           # Time-decay system
│   ├── eligibility.py      # Rule-based scheme matching
│   ├── translation.py      # Multilingual support
│   └── tts.py              # Text-to-speech
├── Data/                   # Policy datasets (10 policies × 3 modalities)
├── app.py                  # Streamlit UI (660 lines)
├── cli.py                  # Data ingestion CLI
├── run_evaluation.py       # Test suite
├── requirements.txt        # Dependencies (21 packages)
└── setup.{bat,sh}          # One-click setup scripts
```

## Policies Covered

| Policy | Period | Data Points | Notes |
|--------|--------|-------------|-------|
| NREGA | 2005-2025 | 131 chunks | Employment guarantee |
| RTI | 2005-2025 | 108 chunks | Right to information |
| PM-KISAN | 2019-2025 | 54 chunks | Farmer income support |
| Ayushman Bharat | 2018-2025 | 62 chunks | Health insurance |
| Swachh Bharat | 2014-2025 | 71 chunks | Sanitation mission |
| Digital India | 2015-2025 | 68 chunks | Digital infrastructure |
| Make in India | 2014-2025 | 59 chunks | Manufacturing |
| Skill India | 2015-2025 | 65 chunks | Vocational training |
| Smart Cities | 2015-2025 | 62 chunks | Urban development |
| NEP | 2020-2025 | 43 chunks | Education policy |

Total: 847 chunks ingested (as of last count)

## License

GPL-3.0

## Acknowledgments

Built for the AI for Community Impact hackathon. We wanted to show that useful policy tools can be built with open-source components and modest hardware. The core retrieval and drift detection runs entirely offline once data is ingested.

This is a prototype. It demonstrates feasibility. Production deployment would require significant additional work on data quality, authentication, scale, and monitoring.
