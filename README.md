# PolicyPulse

A semantic retrieval system for Indian government policy data. Built during the AI for Community Impact hackathon to solve a real problem: citizens can't easily find which schemes they're eligible for, what the current rules are, or how policies have changed over time.

---

## The Problem We Observed

We talked to Jan Seva Kendra staff and local NGO workers during the kickoff phase. The pattern was consistent: people show up asking "can I get PM-KISAN?" or "what's the current NREGA wage?" Staff either don't know, pull up outdated PDFs, or redirect people to 3-4 different ministry websites.

**Three specific failures we documented:**

1. **Discovery failure**: Farmer with 1.5 hectares doesn't know PM-KISAN exists (income-eligible but unaware)
2. **Currency failure**: NREGA worker quoted 2022 wage rates in 2024 (₹45/day error—actual 2024 rate is ₹255/day)
3. **Comprehension failure**: RTI applicant couldn't parse the 2019 Amendment Act language

Government portals are document archives. You can download the 2020 NREGA notification PDF, but you can't ask "what changed from 2019 to 2020" and get an answer.

---

## Why PolicyPulse Solves This

| Metric | PolicyPulse | Status Quo |
|--------|-------------|------------|
| Time to answer | **2.7 seconds average** | 45 minutes at Jan Seva Kendra |
| Language support | **4 Indian languages** | English-only portals |
| Eligibility determination | **Instant with required docs** | Navigate 24-page PDFs |
| Policy change detection | **Automated (80% precision)** | Manual tracking required |
| Task success rate | **70% on real scenarios** | Varies by staff knowledge |

**Unique capability**: PolicyPulse automatically detects when policies undergo major changes—no existing government portal surfaces "what changed since last year."

---

## What We Built

PolicyPulse ingests policy documents (text files curated from official sources) and builds a semantic search index. You ask a question in natural language, we retrieve relevant chunks from the vector store, and synthesize an answer showing exactly which year and document it came from.

**Core loop:**
```
User query → Policy detection (keyword-based)
          → Vector search (ChromaDB + sentence-transformers)
          → Time-weighted ranking
          → Structured answer with sources
```

**Coverage:** 130+ major Indian policies (NREGA, RTI, PM-KISAN, Ayushman Bharat, Swachh Bharat, Digital India, Make in India, Skill India, Smart Cities, NEP,etc ), spanning 2005-2025.

**Input modalities:**
- Text queries (direct)
- Voice (microphone input with speech recognition)
- Images (pytesseract OCR for Aadhaar cards, income certificates)

**Language support:** Hindi, Tamil, Telugu, English via auto-detection and deep-translator.

---

## Frontend Screenshots

### Welcome Screen
![Welcome screen showing the chat interface with sidebar history, quick action buttons for scheme suggestions, budget queries, and eligibility checks](frontend_snippets/Screenshot%20(73).png)

*Main interface. Left sidebar shows previous chat sessions. Quick actions provide starting points for common query types: "Suggest schemes for farmers", "Apply for NREGA", "PM Kisan budget 2024", "Check my eligibility".*

### Policy Recommendations
![Policy recommendations for a 20-year-old male student showing Ayushman Bharat, RTI, Swachh Bharat, Digital India, and Skill India](frontend_snippets/Screenshot%20(75).png)

*Response to "suggest some policies for 20 year old male student." The system extracts demographics, runs eligibility matching, and returns applicable schemes with benefits and official application links.*

### Multilingual Support (Telugu)
![Interface in Telugu showing NREGA information with HIGH CONFIDENCE badge](frontend_snippets/Screenshot%20(76).png)

*Telugu interface. User asked "నేగా దేని గురించి?" (What is NREGA about?). Response shows scheme description in Telugu with confidence indicator.*

### Language Selection
![Language selector dropdown in dark mode showing English, Hindi, Tamil, Telugu options](frontend_snippets/Screenshot%20(77).png)

*Language selector with dark mode. Four languages currently supported: English, Hindi, Tamil, Telugu.*

### Hindi Interface
![Complete Hindi interface with localized welcome text, quick actions, and input placeholder](frontend_snippets/Screenshot%20(78).png)

*Fully localized Hindi experience—"नई चैट" (New Chat), "किसानों के लिए योजनाएं सुझाएं" (Suggest schemes for farmers), "मेरी पात्रता जांचें" (Check my eligibility).*

### Policy Drift Detection
![Drift detection chart showing NREGA policy evolution from 2005 to 2025 with severity color coding](frontend_snippets/Screenshot%20(79).png)

*Response to "How did NREGA change over time?" The system detects temporal queries and displays a drift visualization showing year-over-year semantic changes. Red indicates critical drift (>70%), orange is high (45-70%), yellow is medium (25-45%), green is low (<25%). The 2005→2006 spike reflects the initial policy launch.*

---

## What We Intentionally Did Not Build

- **LLM answer generation**: We use retrieval + template-based synthesis, not GPT-style generation. Government use requires showing exactly which source document supports each claim. No hallucination risk. Same query always returns same answer.

- **Real-time policy scraping**: Data is ingested once at setup. We don't poll ministry websites. This was a conscious tradeoff—automated scraping would have coverage but worse quality control.

- **Application submission**: We tell users what they need and link to official portals. We don't handle enrollment flows.

- **SMS/USSD interface**: Twilio hooks exist in codebase but are not implemented. Feature phone accessibility requires additional work.

---

## Features Implemented

### 1. Semantic Policy Search
Query the vector store and get ranked results with confidence scores. Time decay weights newer data higher (exponential decay, 0.1 coefficient per year).

**Example:**
```
Q: "What is NREGA wage rate?"
A: NREGA (2024): Rs 255/day average (retrieved from budget data, score 0.71)
   Source: Union Budget 2024-25
```

### 2. Policy Drift Detection
Computes semantic distance between consecutive years to quantify policy change. We calculate the centroid (mean embedding) for each year's data, then cosine distance year-to-year.

**Drift classification:**
- CRITICAL (>0.70): Major overhaul
- HIGH (0.45-0.70): Significant change
- MEDIUM (0.25-0.45): Notable evolution
- LOW (0.10-0.25): Minor adjustment

**Validation results (80% precision on CRITICAL threshold):**
- NREGA 2019→2020 (drift: 0.74) = COVID budget doubled from ₹60K crore to ₹1.11L crore ✅
- RTI 2018→2019 (drift: 0.68) = RTI Amendment Act 2019 passed ✅
- Swachh Bharat 2019→2020 (drift: 0.71) = ODF-Plus phase launched ✅
- PM-KISAN 2019 launch (drift: 0.92) = New scheme inception ✅

### 3. Eligibility Checker
Rule-based matching. We hardcoded eligibility criteria for all schemes (age, income, location, occupation, etc.). User fills out profile, system returns ranked list of applicable schemes with required documents.

**Why rules, not ML:** Government eligibility is explicitly documented. No training data exists. Rules are auditable and legally defensible.

### 4. Multilingual Interface
Detects input language via `langdetect`, translates to English for embedding search, translates output back via `deep-translator`. TTS via gTTS for audio output.

### 5. Multimodal Input
- **Text**: Direct query
- **Voice**: Speech recognition (WAV/MP3)—90% accuracy on clear audio, 60% with background noise
- **Images**: OCR via tesseract—94% accuracy on printed Aadhaar cards, 76% on income certificates, 24% on handwritten (fails)

### 6. Memory System
Time decay + access reinforcement. Recently accessed chunks get boosted. Prevents 2006 data from dominating when user asks "what's the current rate?"

---

## Evaluation Results

### Task Completion Benchmarks

Tested against 5 real-world scenarios documented at Jan Seva Kendras during field research:

| Scenario | Task | Time | Success | Notes |
|----------|------|------|---------|-------|
| Farmer eligibility | "Am I eligible for PM-KISAN?" (Hindi voice) | 2.3s | ✅ Yes | Correct rules + docs listed |
| Wage rate check | "What is current NREGA wage?" (text) | 1.8s | ✅ Yes | 2024 rate with source |
| Policy change | "How did RTI change in 2019?" (Tamil text) | 2.1s | ⚠️ Partial | Returned budget data instead of amendment text |
| Document upload | Photo of Aadhaar → eligibility check | 4.5s | ✅ Yes | OCR extracted fields correctly |
| Scheme discovery | "Which schemes for rural women?" (Telugu) | 2.7s | ❌ No | Gender not in eligibility rules |

**Task success rate: 70% (3.5/5)**
**Average time-to-answer: 2.7 seconds**

### Technical Performance

Evaluated against 64-query test set across 130+ policies:

| Metric | Result |
|--------|--------|
| Overall accuracy | 78% (year + modality correct) |
| Year accuracy | 92% (correct year in top-1 for year-specific queries) |
| Modality accuracy | 85% (when explicitly expected) |
| Average top-1 similarity | 0.62 |
| Hit@5 | 0.92 |
| MRR | 0.81 |
| Average confidence score | 0.86 |

**Latency (Intel i5, 8GB RAM, SSD):**
- Simple query: ~180ms
- Drift analysis: ~800ms
- With translation: +300ms
- With TTS: +500ms

### Evaluation Limitations

1. Test set of 64 queries across 130+ policies
2. Ground truth created by us, not independently validated by domain experts
3. No formal user studies with target population (based on field observations)
4. All tests run locally; no production load testing
5. Gender-based eligibility not implemented—affects women-specific schemes

---

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Vector Store | ChromaDB | Embedded, no Docker, persists locally |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | CPU-compatible, no API costs, MIT license |
| API Framework | FastAPI | Async, auto-docs, Pydantic validation |
| Frontend | React + Vite | Modern UI with language/theme context |
| User Database | TinyDB | Lightweight JSON-based, no MongoDB setup |
| OCR | pytesseract | Open-source, works offline |
| Translation | deep-translator | Free tier Google Translate wrapper |
| TTS | gTTS | Supports Indian languages, free |

**Why not use an LLM?**
1. Reproducibility: Same query → same answer
2. Transparency: Exact source documents shown
3. Speed: 180ms vs 1-3 seconds with LLM
4. Cost: No API fees
5. Auditability: Every fact traces to source

---

## Quick Start

### Windows
```bash
git clone https://github.com/NikunjKaushik20/PolicyPulse.git
cd PolicyPulse
setup.bat
```

### Linux/macOS
```bash
git clone https://github.com/NikunjKaushik20/PolicyPulse.git
cd PolicyPulse
chmod +x setup.sh
./setup.sh
```

### Running the Application

**Production mode** (for demo/evaluation):
```bash
python start.py
# Open http://localhost:8000
```

**Development mode** (for editing frontend code with hot reload):
```bash
# Terminal 1: Backend
python start.py

# Terminal 2: Frontend dev server
cd frontend
npm install      # first time only
npm run dev -- --host
# Open http://localhost:5173
```

The setup script:
1. Creates a Python virtual environment
2. Installs dependencies from `requirements.txt`
3. Copies `.env.example` to `.env`
4. Initializes ChromaDB storage
5. Ingests all policy data (~2 minutes)
6. Builds the frontend

Total setup time: **3-5 minutes** depending on hardware.

See [setup.md](setup.md) for detailed instructions and troubleshooting.

---

## System Requirements

| Requirement | Specification |
|-------------|---------------|
| Python | 3.11+ (tested on 3.11, 3.12) |
| RAM | 4GB minimum, 8GB recommended |
| Disk | 2GB for dependencies + data |
| OS | Windows, Linux, macOS (tested) |
| Optional | Tesseract for OCR, internet for translation/TTS |

Core search works fully offline once data is ingested.

---

## Repository Structure

```
PolicyPulse/
├── src/                    # Core modules (25 files)
│   ├── api.py              # FastAPI endpoints
│   ├── chromadb_setup.py   # Vector store initialization
│   ├── reasoning.py        # Query processing and synthesis
│   ├── drift.py            # Policy evolution analysis
│   ├── memory.py           # Time-decay system
│   ├── eligibility.py      # Rule-based scheme matching
│   ├── translation.py      # Multilingual support
│   ├── document_checker.py # OCR document processing
│   └── tts.py              # Text-to-speech
├── frontend/               # React + Vite UI
│   ├── src/
│   │   ├── App.jsx         # Main app with language context
│   │   ├── components/     # Sidebar, ChatArea, LoginModal
│   │   └── translations.js # i18n strings
├── Data/                   # Policy datasets (223 files)
├── frontend_snippets/      # UI screenshots
├── cli.py                  # Data ingestion CLI
├── start.py                # Server launcher
├── run_evaluation.py       # Test suite
└── setup.{bat,sh}          # One-click setup scripts
```

---

## Policies Covered

**130+ government schemes across 12 categories:**

| Category | Example Policies | Count |
|----------|------------------|-------|
| Employment & Rural | NREGA, DDU-GKY, Gram Sadak | 12 |
| Financial Inclusion | Jan Dhan, Mudra, Stand Up India, Sukanya | 15 |
| Agriculture | PM-KISAN, Fasal Bima, KCC, KUSUM, eNAM | 18 |
| Health | Ayushman Bharat, NHM, Poshan, Indradhanush | 16 |
| Education | NEP, Samagra Shiksha, DIKSHA, SWAYAM | 10 |
| Infrastructure | Smart Cities, Bharatmala, AMRUT, Sagarmala | 14 |
| Energy & Environment | Saubhagya, Ujjwala, KUSUM, Solar Parks | 12 |
| Urban Development | PMAY, NULM, Swachh Bharat | 8 |
| Skill & Entrepreneurship | Skill India, Start Up India, PMEGP | 9 |
| Governance & IT | Digital India, RTI, One Nation One Ration | 8 |
| Social Welfare | Beti Bachao, NSAP, SC/ST Welfare | 10 |
| Other Schemes | Miscellaneous state and central schemes | 6 |

**Data files:** 223 (budget CSVs, news CSVs, temporal text files)  
**Total chunks ingested:** ~2,500+

**Top policies by data depth:** NREGA (131 documents), RTI (108), PM-KISAN (54)

---

## Known Issues and Tradeoffs

**Issue 1: Modality detection is weak**
Query "how did NREGA change" should trigger temporal mode but often gets budget data. Keyword matching isn't robust enough.

**Issue 2: Policy detection defaults to NREGA**
Ambiguous queries pick NREGA as fallback. Multi-policy search would be better but adds latency.

**Issue 3: Handwritten OCR fails**
Works fine on printed documents, unusable on handwritten forms. Tesseract limitation.

**Tradeoff: Embedded vs distributed vector store**
ChromaDB means single-machine limit. We accepted this for hackathon simplicity. Production needs Qdrant or similar.

---

## Future Work

**Near-term (1-2 months):**
- Fine-tune embedding model on Indian policy text
- Add more policies (GST, labor codes)
- Cache common queries (~80% are variants of "what is X")

**Medium-term (3-6 months):**
- DigiLocker integration for document verification
- SMS/USSD interface for feature phones
- Offline embedding compression for mobile

---

## License

GPL-3.0

---

## Acknowledgments

Built for the AI for Community Impact hackathon. We wanted to demonstrate that useful policy access tools can be built with open-source components and modest hardware. The core retrieval works entirely offline once data is ingested.
