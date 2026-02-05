# Architecture

This document describes the technical architecture of PolicyPulse—the components, data flow, design decisions, and failure modes.

---

## High-Level Overview

PolicyPulse is a retrieval-augmented system with four main layers:

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                          │
│  Streamlit UI  |  FastAPI REST  |  Voice/SMS (planned)     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Processing Layer                         │
│  Query Detection  |  Translation  |  Multimodal Input      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Reasoning Layer                          │
│  Semantic Search  |  Drift Analysis  |  Eligibility Check  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer                           │
│  ChromaDB (vectors)  |  File-based data  |  Logs           │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Query Processing Flow

1. **Input Reception**
   - User submits query via Streamlit UI, REST API, or (planned) SMS
   - If multimodal: OCR for images, speech recognition for audio/video

2. **Policy Detection**
   - Keyword-based matching against known policy terms
   - Example: "NREGA", "100 days employment", "rural guarantee" → NREGA
   - Fallback to most semantically similar policy centroid; in ambiguous cases NREGA is often selected due to query distribution in our dataset

3. **Translation (Optional)**
   - If source language ≠ English, translate to English for embedding
   - deep-translator (Google Translate API wrapper)

4. **Vector Search**
   - Query text embedded via sentence-transformers
   - ChromaDB returns top-k similar chunks with cosine distance

5. **Answer Synthesis**
   - Group retrieved chunks by modality (temporal/budget/news)
   - Combine into structured response (template-based, not generative)
   - Calculate confidence score from retrieval distances

6. **Output Formatting**
   - Apply time-decay weights for recency
   - Translate response to target language if needed
   - Generate TTS audio if requested

---

## Component Details

### ChromaDB Setup (`src/chromadb_setup.py`)

**Purpose**: Persistent vector storage without Docker dependency.

**Design decisions**:
- Chose ChromaDB over Qdrant because ChromaDB is pure Python, embeds in process
- Qdrant requires Docker or separate server—deployment complexity we wanted to avoid
- ChromaDB's `PersistentClient` stores to `./chromadb_data/` directory

**Collection schema**:
```
Collection: policy_data
├── document: text content
├── embedding: 384-dim vector (auto-generated)
└── metadata:
    ├── policy_id: "NREGA", "RTI", etc.
    ├── year: "2020", "2021", etc.
    ├── modality: "temporal" | "budget" | "news"
    ├── sentiment: "positive" | "neutral" | "negative"
    ├── decay_weight: 0.0-1.5 (time decay + access boost)
    └── access_count: integer
```

**Failure modes**:
- Corrupted SQLite database (ChromaDB's backend) → `reset-db` CLI command
- Embedding model fails to load (OOM) → reduce batch size or use CPU-only

---

### Reasoning Engine (`src/reasoning.py`)

**Purpose**: Convert retrieval results into structured answers.

**Process**:
1. Parse ChromaDB query results (ids, documents, metadatas, distances)
2. Format each result with rank, score, preview
3. Group by modality for multi-source answers
4. Calculate confidence from top-3 average similarity

**Confidence thresholds**:
- ≥0.70: High confidence → reliable answer
- 0.45-0.70: Medium confidence → likely correct but verify
- <0.45: Low confidence → may be missing relevant data

**Why not use an LLM?**
- Reproducibility: same query always returns same answer
- Transparency: we show exact source documents, no hallucination risk
- Speed: retrieval is ~180ms, LLM would add 1-3 seconds
- Cost: no API fees for core functionality

---

### Drift Analysis (`src/drift.py`)

**Purpose**: Quantify how a policy has changed semantically over time.

**Algorithm**:
1. Retrieve all embeddings for a policy, grouped by year
2. Compute centroid (mean vector) for each year
3. Calculate cosine similarity between consecutive year centroids
4. Convert to drift score: `drift = 1 - similarity`

**Severity classification**:
| Drift Score | Severity | Meaning |
|------------|----------|---------|
| >0.70 | CRITICAL | Major policy overhaul |
| 0.45-0.70 | HIGH | Significant changes |
| 0.25-0.45 | MEDIUM | Notable evolution |
| 0.10-0.25 | LOW | Minor adjustments |
| <0.10 | MINIMAL | Stable policy |

**Example finding**: NREGA 2019→2020 shows CRITICAL drift (0.74) corresponding to COVID emergency expansion from Rs 60,000 crore to Rs 1.11 lakh crore.

**Limitations**:
- Requires ≥2 years of data per policy
- Semantic drift doesn't always mean substantive change (could be phrasing)
- Needs Qdrant for production drift analysis (ChromaDB lacks scroll API). For this prototype, yearly aggregation sizes are small enough to be handled in-memory.

---

### Memory System (`src/memory.py`)

**Purpose**: Weight recent and frequently-accessed information higher.

**Time decay**:
```python
decay_weight = exp(-0.1 * age_years)
```
- 1 year old: 0.90 weight
- 5 years old: 0.61 weight
- 10 years old: 0.37 weight

**Access reinforcement**:
- Each query that returns a chunk increases its `access_count`
- Boost multiplier: `min(0.02 * access_count, 1.3)`
- Prevents runaway boosting with cap at 1.3x

**Why this matters**:
- Someone asking about NREGA wages needs 2024 rates, not 2006 rates
- But historical questions ("When was RTI passed?") should find 2005 data
- Decay + access creates natural ranking without manual curation

---

### Eligibility Checker (`src/eligibility.py`)

**Purpose**: Rule-based matching of user profiles to schemes.

**Rules structure** (example for NREGA):
```python
{
    "location_type": ["rural"],  # Must be rural
    "age_min": 18,
    "willingness_manual_work": True
}
```

**Matching logic**:
- All rules must pass for eligibility
- Partial matches not shown (too confusing for users)
- Order by priority: PM-KISAN, AYUSHMAN-BHARAT, NREGA are HIGH priority

**Why rule-based, not ML?**
- Government eligibility criteria are explicit and documented
- No training data for eligibility classification
- Rules can be audited; ML model is a black box
- Updates are straightforward when policies change

---

### Multimodal Input (`app.py`)

**Image processing**:
- PIL loads image from upload
- pytesseract extracts text via OCR
- Works for: Aadhaar cards, income certificates, land records

**Audio processing**:
- SpeechRecognition library with Google Web Speech API
- Supports: MP3, WAV formats
- Limitation: needs internet connection

**Video processing**:
- PyAV extracts audio stream from video container
- Converts to WAV format in memory
- Same speech recognition pipeline as audio

**Failure modes**:
- OCR on handwritten documents is unreliable
- Speech recognition fails on strong accents or background noise
- Video without audio track returns empty

---

### Translation (`src/translation.py`)

**Implementation**:
- deep-translator library wrapping Google Translate
- Falls back gracefully if translation fails (returns original)

**Supported languages**:
```
en, hi, ta, te, bn, mr, gu, kn, ml, pa
```

**What gets translated**:
- Final answer text
- Retrieved document previews
- NOT metadata (policy names, years stay in English)

---

### Text-to-Speech (`src/tts.py`)

**Implementation**:
- gTTS (Google Text-to-Speech), free tier
- Returns MP3 audio bytes

**Use case**:
- Voice-first interface for low-literacy users
- Accessibility for visually impaired

**Pre-computed common phrases**:
```python
COMMON_PHRASES_HINDI = {
    'welcome': 'नागरिक मित्र में आपका स्वागत है',
    'searching': 'खोज रहा हूं...',
    ...
}
```

---

## API Design

**Rate limiting**: 200 requests/minute default, 20/minute for heavy endpoints (query)

**Key endpoints**:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/query` | POST | Semantic search with reasoning |
| `/drift/{policy_id}` | GET | Policy evolution analysis |
| `/recommendations/{policy_id}` | GET | Related policies |
| `/eligibility/check` | POST | User profile matching |
| `/translate` | POST | Text translation |
| `/tts` | POST | Text-to-speech audio |
| `/document/upload` | POST | OCR document processing |

---

## Security Considerations

**Current state**:
- No authentication (prototype)
- Rate limiting prevents DoS
- Input validation via Pydantic models
- Query length limits (3-500 characters)

**For government deployment would need**:
- API key authentication
- Aadhaar-based user verification
- Audit logging with IP and session tracking
- HTTPS enforcement
- Input sanitization for injection attacks

---

## Scalability

**Current limits**:
- Single-process FastAPI server
- ChromaDB embedded (not distributed)
- Embedding model loaded in memory (~400MB)

**Scaling path**:
1. **Horizontal API scaling**: Stateless FastAPI behind load balancer
2. **Vector store**: Migrate ChromaDB to Qdrant cluster or Pinecone
3. **Embedding service**: Dedicated GPU inference server
4. **Caching**: Redis for common queries

**Estimated capacity** (single server, 8GB RAM):
- ~50 concurrent users
- ~10 queries/second sustained
- ~100k documents in index

---

## Failure Handling

| Component | Failure | Handling |
|-----------|---------|----------|
| ChromaDB | Corrupt database | CLI `reset-db` + re-ingest |
| Embedding model | OOM | Reduce batch size, use CPU |
| Translation API | Timeout | Return original text |
| Speech recognition | No internet | Error message, suggest text input |
| OCR | Unreadable image | Error with suggestions |

---

## Why These Technology Choices

| Choice | Reason | Alternative Rejected |
|--------|--------|---------------------|
| ChromaDB | No Docker, pure Python, persistent | Qdrant (needs Docker), FAISS (no persistence) |
| sentence-transformers | Quality/speed balance, MIT license | OpenAI embeddings (cost, privacy), custom model (training effort) |
| FastAPI | Async, auto-docs, Python native | Flask (sync), Django (overkill) |
| Streamlit | Rapid prototyping for demo | React (more dev time), Gradio (less flexible) |
| gTTS | Free, 10 languages | Google Cloud TTS (cost), pyttsx3 (quality) |

---

## Architecture Tradeoffs

**Retrieval-only vs. RAG with LLM**:
- We chose retrieval-only for transparency and reproducibility
- Downside: less natural language fluency in answers
- Acceptable for government use case where accuracy > eloquence

**Embedded vs. client-server vector store**:
- ChromaDB embedded means single-machine limit
- Upside: zero infrastructure, runs on laptop
- Migration path to Qdrant cluster is straightforward

**Rule-based eligibility vs. ML classification**:
- Rules are auditable and match official criteria exactly
- Downside: manual updates when policies change
- Acceptable for 10 schemes; would need automation at scale
