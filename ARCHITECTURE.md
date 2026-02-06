# PolicyPulse Architecture

This document describes the system architecture as implemented. Every component maps to actual source files.

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React Frontend                                │
│   frontend/src/App.jsx                                              │
│   - LanguageContext (EN/HI/TA/TE)                                   │
│   - ThemeContext (light/dark)                                       │
│   - AuthContext (JWT tokens)                                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ HTTP/REST
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                               │
│   src/api.py (596 lines)                                            │
│   Endpoints: /query, /auth/*, /history, /translate, /tts, /upload   │
└──────┬──────────────────┬───────────────────┬───────────────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌──────────────┐  ┌───────────────┐  ┌─────────────────┐
│  ChromaDB    │  │   Reasoning   │  │   Translation   │
│  (Vector DB) │  │    Engine     │  │  deep-translator│
│              │  │               │  │                 │
│ 384-dim vecs │  │ synthesize_   │  │ 9 languages     │
│ ~850 chunks  │  │ answer()      │  │ supported       │
└──────────────┘  └───────────────┘  └─────────────────┘
       │                  │
       ▼                  ▼
┌──────────────┐  ┌───────────────┐
│  Embeddings  │  │  Eligibility  │
│  all-MiniLM  │  │  Rule Engine  │
│  L6-v2       │  │               │
└──────────────┘  └───────────────┘
```

---

## Component Details

### 1. Frontend (React + Vite)

**Location:** `frontend/src/`

**Key files:**
- `App.jsx` - Main component, manages language/theme/auth contexts
- `components/Sidebar.jsx` - Chat history sidebar
- `components/ChatArea.jsx` - Main chat interface with message display
- `components/LoginModal.jsx` - JWT authentication UI
- `translations.js` - i18n strings for EN, HI, TA, TE

**Data flow:**
```
User types query
    → handleSendMessage()
    → POST /query with { query_text, session_id, demographics, language }
    → Response rendered in ChatArea
    → Session stored in sidebar history
```

**Why React over Streamlit:**
We started with Streamlit (see old `app.py`). Switched to React for:
1. Better state management (contexts vs session_state hacks)
2. Proper dark mode theming
3. Responsive sidebar behavior
4. JWT auth integration felt cleaner

### 2. API Layer (FastAPI)

**Location:** `src/api.py` (596 lines)

**Endpoints:**

| Route | Method | Purpose |
|-------|--------|---------|
| `/query` | POST | Main policy search endpoint |
| `/auth/signup` | POST | User registration |
| `/auth/login` | POST | JWT token generation |
| `/auth/me` | GET | Current user info |
| `/history` | GET | List past chat sessions |
| `/history/{id}` | GET | Messages for specific session |
| `/translate` | POST | Text translation |
| `/tts` | POST | Text-to-speech audio |
| `/upload` | POST | Document OCR processing |
| `/eligibility` | POST | Check scheme eligibility |

**Authentication:**
- JWT tokens via `python-jose`
- Password hashing via `passlib[bcrypt]`
- User data stored in TinyDB (`policypulse_db.json`)

**Why TinyDB over MongoDB:**
Original design used MongoDB. TinyDB eliminated:
- Docker container management
- Connection string configuration
- Production database ops overhead

For a hackathon demo with <100 users, JSON file storage is adequate.

### 3. Vector Store (ChromaDB)

**Location:** `src/chromadb_setup.py` (271 lines)

**Configuration:**
```python
CHROMADB_DIR = "./chromadb_data"
COLLECTION_NAME = "policy_data"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2
```

**Key functions:**
- `get_collection()` - Returns or creates the policy_data collection
- `add_documents(documents, metadatas, ids)` - Bulk insert with embeddings
- `query_documents(query_text, n_results, where)` - Semantic search with filters
- `get_collection_info()` - Statistics and policy breakdown

**Why ChromaDB over Qdrant:**
Comment from source code:
```python
# Migrated from Qdrant Jan 2024 - setup was too painful for hackathon judges
# ChromaDB just works out of the box, worth the API differences
```

Qdrant required Docker. ChromaDB is pure Python with SQLite backend.

**Metadata schema per document:**
```python
{
    "policy_id": "NREGA",      # Normalized policy identifier
    "year": "2023",            # Data year
    "modality": "budget",      # budget | news | temporal
    "source": "Union Budget",  # Original source
    "access_count": 0,         # For memory reinforcement
    "decay_weight": 1.0        # Time decay multiplier
}
```

### 4. Query Processing

**Location:** `src/query_processor.py` (315 lines)

**Pipeline:**
```
Raw query
    → detect_policy_from_query()  # Keyword matching, EN + HI
    → extract_years_from_query()  # Regex for 4-digit years
    → extract_demographics()      # Age, occupation, category
    → build_query_filter()        # ChromaDB where clause
    → Return enhanced context
```

**Policy aliases (partial list from code):**
```python
POLICY_ALIASES = {
    'nrega': 'NREGA',
    'mgnrega': 'NREGA',
    'एनआरेगा': 'NREGA',
    'मनरेगा': 'NREGA',
    'pm kisan': 'PM-KISAN',
    'पीएम किसान': 'PM-KISAN',
    # ... 50+ aliases
}
```

**Year extraction patterns:**
```python
# Catches: "budget 2020", "between 2019 and 2021", "from 2015 to 2020"
r'\b(20\d{2})\b'  # Simple 4-digit year
r'between\s+(\d{4})\s+and\s+(\d{4})'  # Range
r'from\s+(\d{4})\s+to\s+(\d{4})'  # Range
```

### 5. Reasoning Engine

**Location:** `src/reasoning.py` (379 lines)

**Main functions:**

`generate_reasoning_trace(query, retrieved_results, context)`:
1. Analyze retrieved documents for policy/modality/year
2. Score relevance based on similarity scores
3. Generate structured reasoning steps
4. Return dict with `reasoning_steps`, `final_answer`, `confidence`

`synthesize_answer(query, retrieved_points, context)`:
- Template-based answer construction
- Handles: definitions, budget queries, eligibility, temporal queries
- Injects official application URLs from `policy_urls.py`

**Answer structure:**
```python
{
    "final_answer": "NREGA provides 100 days of guaranteed...",
    "confidence_score": 0.86,
    "reasoning_steps": [...],
    "sources": [
        {"policy": "NREGA", "year": "2024", "type": "budget"}
    ]
}
```

### 6. Eligibility Engine

**Location:** `src/eligibility.py` (376 lines)

**Rule structure (from code):**
```python
ELIGIBILITY_RULES = {
    "NREGA": {
        "name": "Mahatma Gandhi National Rural Employment Guarantee Act",
        "description": "100 days of guaranteed wage employment",
        "rules": {
            "age_min": 18,
            "location_type": ["rural"],
            "willingness_manual_work": True
        },
        "documents_required": [
            "Aadhaar card",
            "Job card",
            "Bank account details"
        ],
        "application_link": "https://nrega.nic.in/",
        "benefits": "100 days employment at ₹255/day (2024)"
    },
}
```

**Matching logic (`check_eligibility`):**
1. For each policy, check each rule against user profile
2. Track matched/unmatched rules
3. Calculate match percentage
4. Return policies where match >= 80%

**Limitation noted in code:**
```python
# NOTE: Gender not currently in rules
# Would need to add for women-specific schemes like BBBP
```

### 7. Memory System

**Location:** `src/memory.py` (341 lines)

**Two mechanisms:**

1. **Time decay:** Older documents get lower weight
```python
DECAY_COEFFICIENT = 0.1  # Per year
MIN_DECAY_WEIGHT = 0.3   # Floor
MAX_DECAY_WEIGHT = 1.5   # Ceiling

def apply_time_decay(policy_id, current_year=2026):
    # weight = max(MIN, 1.0 - (current_year - doc_year) * DECAY_COEFFICIENT)
```

2. **Access reinforcement:** Frequently accessed docs get boosted
```python
REINFORCEMENT_AMOUNT = 0.05  # Per access

def reinforce_memory_batch(point_ids):
    # Increment access_count, boost decay_weight
```

**Why both mechanisms:**
- Time decay prevents 2006 data from dominating "current rate" queries
- Reinforcement learns which docs are actually useful

### 8. Translation Layer

**Location:** `src/translation.py` (145 lines)

**Supported languages:**
```python
LANGUAGE_CODES = {
    'english': 'en', 'hindi': 'hi', 'tamil': 'ta', 'telugu': 'te',
    'bengali': 'bn', 'marathi': 'mr', 'gujarati': 'gu',
    'kannada': 'kn', 'malayalam': 'ml', 'punjabi': 'pa'
}
```

**Flow:**
```
Input (any language)
    → detect_language() via langdetect
    → translate_text() to English for embedding
    → Query ChromaDB
    → translate_response() back to original language
```

**Note from code:**
```python
# Switched from googletrans after it broke in Jan 2024 (httpx version conflict)
# deep-translator is more reliable
```

### 9. Document Processing

**Location:** `src/document_checker.py` (487 lines)

**OCR pipeline:**
```
Image upload
    → extract_text_from_image() via pytesseract
    → detect_document_type() via keyword matching
    → extract_fields() using regex patterns
    → validate_document() against expected format
    → Return structured data
```

**Supported documents:**
```python
DOCUMENT_PATTERNS = {
    'aadhaar': {
        'keywords': ['aadhaar', 'आधार', 'government of india'],
        'number_pattern': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        'required_fields': ['name', 'aadhaar_number', 'dob']
    },
    'pan': {...},
    'ration_card': {...}
}
```

**Honest limitation from code:**
```python
# OCR quality is... variable. Hindi works ok, Tamil is rough
# might need to add tesseract language packs per deployment

# NOTE: we tested with caste certificates too but accuracy was <60%
# would need more training data to add
```

---

## Data Flow: Complete Query

1. **Frontend** sends POST to `/query`:
```json
{
    "query_text": "NREGA budget 2023",
    "session_id": "abc-123",
    "language": "en"
}
```

2. **API layer** (`api.py`):
   - Validates request via Pydantic
   - Calls `process_query()` for context extraction
   - Calls `query_documents()` for vector search
   - Calls `generate_reasoning_trace()` for answer synthesis
   - Optionally calls `translate_response()` if language != 'en'
   - Stores in chat history (TinyDB)

3. **Query processor** extracts:
   - Policy: `NREGA`
   - Year: `2023`
   - Filter: `{"policy_id": "NREGA", "year": "2023"}`

4. **ChromaDB** returns top-5 matches with distances

5. **Reasoning engine** synthesizes answer from retrieved chunks

6. **Response**:
```json
{
    "final_answer": "In 2023, NREGA received ₹60,000 crore allocation...",
    "confidence_score": 0.96,
    "session_id": "abc-123",
    "sources": [...]
}
```

---

## Security Considerations

**Implemented:**
- JWT authentication with expiry
- Password hashing (bcrypt)
- CORS configured (currently permissive for hackathon)
- Input validation via Pydantic

**Not implemented:**
- Rate limiting (slowapi imported but not wired)
- Audit logging
- HTTPS (assumed reverse proxy handles this)
- Aadhaar-based authentication

---

## Scalability Notes

**Current limits:**
- ChromaDB is file-based, single-process
- TinyDB is single-file JSON
- All in-memory embedding model (~400MB)

**For production:**
- Replace ChromaDB with Qdrant cluster
- Replace TinyDB with PostgreSQL
- Add Redis for session caching
- Load balance FastAPI with gunicorn workers

**Estimated capacity (current setup):**
- ~10 queries/second
- ~50 concurrent users
- ~10,000 documents before sluggishness

---

## Cost Model

**Current (fully offline after setup):**
- $0/month for vector search
- $0/month for embeddings
- Translation: Free tier (500K chars/month)
- TTS: Free (gTTS)

**Optional enhancements:**
- Google Cloud Translation API: $20/million chars
- Gemini API for enhanced answers: $0 (free tier: 60 req/min)
- Twilio SMS: $0.0075/message

---

## Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `src/api.py` | 596 | FastAPI endpoints |
| `src/chromadb_setup.py` | 271 | Vector store |
| `src/reasoning.py` | 379 | Answer synthesis |
| `src/query_processor.py` | 315 | Query understanding |
| `src/eligibility.py` | 376 | Rule matching |
| `src/memory.py` | 341 | Time decay |
| `src/translation.py` | 145 | i18n |
| `src/document_checker.py` | 487 | OCR |
| `src/embeddings.py` | 309 | Vector generation |
| `frontend/src/App.jsx` | 207 | React UI |
