# PolicyPulse System Design

## 1. Design Overview

PolicyPulse implements a retrieval-augmented information system optimized for government policy queries in resource-constrained environments. The architecture prioritizes deterministic behavior, source traceability, and offline operation over generative AI approaches that introduce hallucination risk and API dependencies.

The system operates as a three-tier architecture: a React frontend providing multilingual UI, a FastAPI backend orchestrating query processing, and an embedded ChromaDB vector store enabling semantic search. All components run on a single machine without external service dependencies for core functionality, making deployment feasible at Jan Seva Kendras and Common Service Centers with limited infrastructure.

Design decisions reflect deployment realities: TinyDB replaces MongoDB to eliminate container management, ChromaDB replaces Qdrant to avoid Docker dependencies, and template-based synthesis replaces LLM generation to ensure reproducibility. The system trades horizontal scalability for operational simplicity, accepting single-machine limits in exchange for zero-configuration deployment.

## 2. Architectural Components

### 2.1 API Layer (FastAPI)

**Responsibility:** HTTP endpoint exposure, request validation, authentication, and orchestration of backend services.

**Implementation:** src/api.py (596 lines) exposes 12 REST endpoints including /query (main search), /auth/* (JWT authentication), /history (session management), /translate, /tts, /upload (OCR), and /eligibility. Pydantic models validate all inputs. CORS middleware configured for cross-origin requests.

**Why FastAPI:** Async request handling, automatic OpenAPI documentation, and Pydantic integration provide type safety and performance. Alternative frameworks (Flask, Django) lack native async support or introduce unnecessary ORM complexity for this use case.

**Tradeoffs:** Single-process deployment limits concurrency to ~50 users (NFR-5). Production deployment would require gunicorn with multiple workers, but this introduces shared state challenges with file-based ChromaDB.

**Satisfies requirements:** FR-1 (query endpoint), FR-27-31 (authentication), FR-35 (error handling), FR-38 (WhatsApp webhook).

### 2.2 Vector Store (ChromaDB)

**Responsibility:** Persistent storage and semantic retrieval of 2,500+ policy document chunks using 384-dimensional embeddings.

**Implementation:** src/chromadb_setup.py (271 lines) initializes ChromaDB client with SQLite backend in ./chromadb_data directory. Collection "policy_data" stores documents with metadata (policy_id, year, modality, source, access_count, decay_weight). Query operations support filtering via where clauses and return top-k results with similarity scores.

**Why ChromaDB over Qdrant:** ChromaDB is pure Python with zero external dependencies. Qdrant requires Docker container management, which field testing revealed as a deployment barrier at government service centers. The 180ms query latency difference (ChromaDB: 180ms, Qdrant: ~120ms) is acceptable for this use case.

**Tradeoffs:** File-based storage limits to single process. No horizontal scaling. Concurrent writes are serialized. Collection size limited to ~10,000 documents before performance degradation (NFR-6). Production deployment would require migration to Qdrant cluster or Pinecone.

**Metadata schema design:** Each chunk stores policy_id (normalized identifier), year (string for exact matching), modality (budget/news/temporal for result type filtering), source (provenance), access_count (reinforcement learning), and decay_weight (time-based relevance). This schema enables FR-8 (time decay) and FR-9 (access reinforcement).

**Satisfies requirements:** FR-5 (semantic search), FR-6 (top-k retrieval), FR-34 (metadata storage), NFR-1 (180ms latency), NFR-14 (persistence).

### 2.3 Embedding Model (sentence-transformers)

**Responsibility:** Convert text queries and documents to 384-dimensional dense vectors for semantic similarity computation.

**Implementation:** src/embeddings.py (309 lines) loads all-MiniLM-L6-v2 model from sentence-transformers library. Model runs on CPU, loads once at startup (~400MB memory), and generates embeddings in ~50ms per query.


**Why all-MiniLM-L6-v2:** Balances accuracy and speed for CPU inference. Larger models (all-mpnet-base-v2: 768-dim) provide 2-3% accuracy improvement but 3x slower. Smaller models (all-MiniLM-L12-v2: 384-dim) are faster but 5% less accurate. This model achieves 0.62 average similarity score (NFR-10) meeting accuracy requirements.

**Why local embeddings over API:** Zero cost, no rate limits, offline operation, and data privacy. OpenAI embeddings (text-embedding-3-small) cost $0.02/1M tokens and require internet connectivity. For government deployment, avoiding external API dependencies is critical.

**Tradeoffs:** CPU-only inference limits throughput to ~20 embeddings/second. GPU acceleration would enable 200+ embeddings/second but introduces hardware requirements incompatible with target deployment environments.

**Satisfies requirements:** FR-5 (384-dim embeddings), NFR-10 (0.62 similarity), NFR-26 (400MB memory), NFR-28 (offline operation).

### 2.4 Query Processor

**Responsibility:** Extract structured context (policy identifiers, years, demographics) from natural language queries to construct targeted vector search filters.

**Implementation:** src/query_processor.py (315 lines) implements detect_policy_from_query() using keyword matching against 50+ aliases in English and Hindi, extract_years_from_query() using regex patterns for 4-digit years and ranges, extract_demographics() using pattern matching for age/gender/occupation, and build_query_filter() constructing ChromaDB where clauses.

**Why rule-based over ML:** Policy names and years follow predictable patterns. A trained NER model would require labeled data (none exists), introduce model maintenance burden, and add inference latency. Rule-based extraction achieves 92% year accuracy (NFR-8) and 85% policy detection accuracy, meeting requirements without ML complexity.

**Tradeoffs:** Hardcoded aliases require manual updates when new schemes launch. Multi-policy queries fail because ChromaDB where clauses don't support $or operations cleanly (C-5). Ambiguous queries default to NREGA as fallback, introducing bias.

**Satisfies requirements:** FR-2 (policy detection), FR-3 (year extraction), FR-4 (demographics extraction), NFR-8 (92% year accuracy).

### 2.5 Reasoning Engine

**Responsibility:** Synthesize structured answers from retrieved document chunks using template-based logic and confidence scoring.

**Implementation:** src/reasoning.py (379 lines) implements synthesize_answer() which analyzes retrieved chunks, detects query type (definition/budget/eligibility/temporal), constructs answer from templates, injects official URLs from policy_urls.py, and calculates confidence score based on top-1 similarity (50% weight) and result consistency (50% weight).

**Why template-based over LLM:** Government use requires showing exact source documents for every claim. LLMs introduce hallucination risk—GPT-4 generates plausible but incorrect budget figures 8% of the time in testing. Template synthesis guarantees reproducibility: identical query always returns identical answer (NFR-13). No API costs, no rate limits, no internet dependency.

**Confidence scoring logic:** 
- Top-1 similarity contributes 50% (higher similarity = more confident)
- Result consistency contributes 50% (all top-5 from same policy = more confident)
- Normalized to 0-1 range
- Average confidence 0.86 (NFR-11) indicates reliable scoring

**Tradeoffs:** Templates cannot handle complex multi-hop reasoning ("If I'm eligible for NREGA, am I also eligible for PM-KISAN?"). Answer quality depends on template coverage—unmapped query types return generic responses. LLM would provide more natural language but sacrifice auditability.

**Satisfies requirements:** FR-7 (structured answers), FR-8 (time decay application), NFR-13 (deterministic responses), NFR-18 (confidence scores).

### 2.6 Eligibility Engine

**Responsibility:** Match user demographic profiles against hardcoded eligibility rules for 130+ schemes and return applicable policies.

**Implementation:** src/eligibility.py (376 lines) defines ELIGIBILITY_RULES dictionary with nested rule structures (age_min, age_max, location_type, occupation, income_max, category, gender, scheme-specific conditions). check_eligibility() iterates all policies, calculates match percentage, and returns schemes with ≥80% match including benefits, required documents, and application URLs.


**Why rules over ML:** Government eligibility criteria are explicitly documented in scheme notifications. No training data exists for ML approach. Rules are legally defensible—system can cite exact notification for each eligibility decision. ML model would be a black box incompatible with government accountability requirements.

**Gender-specific rules:** ELIGIBILITY_RULES includes gender field for women-centric schemes (PMMVY, Mahila Samman) satisfying FR-17. Male applicants are correctly excluded from these schemes during matching.

**Tradeoffs:** Rules require manual updates when schemes change. Complex conditions (disability status, land ownership verification) are not implemented due to lack of structured data (OS-7). 80% match threshold is arbitrary—no user research validates this cutoff.

**Satisfies requirements:** FR-14 (rule matching), FR-15 (match scoring), FR-16 (scheme details), FR-17 (gender rules).

### 2.7 Memory System

**Responsibility:** Apply time-based decay and access-based reinforcement to document relevance scores.

**Implementation:** src/memory.py (341 lines) implements apply_time_decay() calculating weight = max(0.3, 1.0 - (2026 - doc_year) * 0.1) and reinforce_memory_batch() incrementing access_count and boosting decay_weight by 0.05 per access.

**Why dual mechanism:** Time decay prevents 2006 NREGA launch data from dominating "current wage rate" queries (addresses documented currency failure). Access reinforcement learns which documents users find useful—frequently accessed chunks get boosted even if older. Combined approach balances recency and utility.

**Decay parameters:** Coefficient 0.1 means 10-year-old data has weight 0.0 (floored to 0.3). Ceiling 1.5 prevents runaway reinforcement. These values were empirically tuned—no formal optimization performed.

**Tradeoffs:** Decay assumes newer data is always better, which fails for historical queries ("What was NREGA wage in 2010?"). Reinforcement creates feedback loops where popular documents become more popular. No decay reset mechanism when policies undergo major changes.

**Satisfies requirements:** FR-8 (time decay), FR-9 (reinforcement), NFR-13 (deterministic with same access patterns).

### 2.8 Translation Layer

**Responsibility:** Detect input language, translate queries to English for embedding, translate responses back to original language.

**Implementation:** src/translation.py (145 lines) uses langdetect for language detection and deep-translator (Google Translate wrapper) for translation. Flow: detect_language() → translate_text(to English) → embed and search → translate_response(to original language).

**Why translate-to-English:** Embedding model (all-MiniLM-L6-v2) is trained primarily on English text. Multilingual models (LaBSE, multilingual-e5) are 3x larger and 2x slower with only marginal accuracy improvement for Indian languages. Translating queries to English before embedding achieves 75% accuracy on Hindi queries (documented in examples.md) at lower computational cost.

**Why deep-translator:** Previous implementation used googletrans library which broke due to httpx version conflicts (documented in code comments). deep-translator is actively maintained and provides stable API. Free tier supports 500K characters/month, sufficient for estimated 500 queries/day * 100 chars/query = 1.5M chars/month (requires paid tier at scale).

**Tradeoffs:** Translation adds 300ms latency (NFR-3). Translation quality varies—technical terms often mistranslated ("wage employment" → "वेतन रोजगार" sometimes becomes "salary job"). Code-switching queries ("NREGA के बारे में बताओ") work because policy detection runs on original text before translation.

**Satisfies requirements:** FR-10 (language detection), FR-11 (query translation), FR-12 (response translation), FR-13 (UI localization), NFR-3 (300ms latency).

### 2.9 Document Processing (OCR)

**Responsibility:** Extract text from uploaded identity documents, detect document type, extract structured fields, and validate format.

**Implementation:** src/document_checker.py (487 lines) uses pytesseract for OCR with 'hin+eng' language pack, keyword matching for document type detection (Aadhaar/PAN/ration card), regex patterns for field extraction (name, number, DOB, gender), and Verhoeff checksum for Aadhaar validation.


**Why pytesseract:** Open-source, works offline, supports Indian languages. Cloud OCR (Google Vision, AWS Textract) provides 5-10% better accuracy but costs $1.50/1000 images and requires internet. For government deployment, offline operation and zero cost outweigh accuracy difference.

**Accuracy by document type:** Printed Aadhaar 94%, income certificates 76%, handwritten forms 56% (documented in examples.md). Handwritten OCR is excluded from production use (OS-8).

**Tradeoffs:** Requires Tesseract installed separately (not Python package). OCR quality degrades with image quality—blurry photos fail. No support for regional language documents beyond Hindi/Tamil/Telugu (OS-15). Aadhaar checksum validation catches format errors but doesn't verify authenticity (would require UIDAI API integration, out of scope).

**Satisfies requirements:** FR-22 (image upload), FR-23 (document type detection), FR-24 (field extraction), FR-25 (validation), FR-26 (TTS).

### 2.10 User Database (TinyDB)

**Responsibility:** Persist user accounts, password hashes, JWT tokens, and chat session history.

**Implementation:** policypulse_db.json stores users table (email, hashed_password, created_at) and sessions table (session_id, user_id, messages array, timestamp). src/auth.py handles bcrypt password hashing and JWT token generation.

**Why TinyDB over MongoDB:** Original design used MongoDB requiring Docker container. Field testing revealed Docker as deployment barrier—service center staff cannot manage containers. TinyDB is single JSON file with zero configuration. Adequate for <100 users (estimated deployment scale).

**Tradeoffs:** No concurrent write safety—race conditions possible with simultaneous signups. No indexing—linear scan for user lookup (acceptable at <100 users). No backup/replication—file corruption loses all data. Production would require PostgreSQL (OS-11).

**Satisfies requirements:** FR-27 (user registration), FR-28 (JWT tokens), FR-29 (token validation), FR-30 (session storage), FR-31 (history retrieval), NFR-21 (password hashing), NFR-15 (persistence).

### 2.11 Frontend (React + Vite)

**Responsibility:** Provide responsive multilingual UI with chat interface, session history, authentication, and theme management.

**Implementation:** frontend/src/App.jsx (207 lines) manages LanguageContext (EN/HI/TA/TE), ThemeContext (light/dark), and AuthContext (JWT). Components: Sidebar.jsx (session history), ChatArea.jsx (message display with confidence badges), InputBar.jsx (text/voice input), LoginModal.jsx (authentication).

**Why React over Streamlit:** Original prototype used Streamlit (app.py exists in repo). Switched to React for: (1) proper state management via contexts vs session_state hacks, (2) responsive sidebar behavior, (3) dark mode theming, (4) JWT auth integration. Streamlit's server-side rendering model caused UI lag with chat history.

**Localization approach:** translations.js contains key-value mappings for 4 languages. UI components read from LanguageContext. This approach is simpler than i18next library for limited language set.

**Tradeoffs:** React requires build step (npm run build) adding deployment complexity. Streamlit would be simpler but lacks UI flexibility. No accessibility testing performed—WCAG compliance unknown.

**Satisfies requirements:** FR-13 (UI localization), NFR-16 (responsive UI), NFR-17 (theme support), NFR-19 (quick actions), NFR-20 (3-5 minute setup).

## 3. Data Flow

### 3.1 Text Query Flow

**Step 1:** User submits query via frontend InputBar → POST /query with {query_text, session_id, language}

**Step 2:** API layer (api.py) validates request via Pydantic QueryRequest model (FR-35, NFR-22)

**Step 3:** Query processor (query_processor.py) extracts policy_id, year range, demographics → constructs ChromaDB where filter (FR-2, FR-3, FR-4)

**Step 4:** Translation layer (translation.py) detects language, translates to English if needed (FR-10, FR-11)

**Step 5:** Embedding model (embeddings.py) generates 384-dim vector from English query (FR-5)

**Step 6:** ChromaDB (chromadb_setup.py) performs similarity search with filter → returns top-5 chunks with scores (FR-6)

**Step 7:** Memory system (memory.py) applies time decay weights and reinforcement to scores (FR-8, FR-9)

**Step 8:** Reasoning engine (reasoning.py) synthesizes answer from chunks using templates → calculates confidence (FR-7)

**Step 9:** Translation layer translates answer back to original language if needed (FR-12)

**Step 10:** API returns {final_answer, confidence_score, sources, session_id}

**Step 11:** Frontend ChatArea renders response with confidence badge and source citations (NFR-18)

**Step 12:** Session stored in TinyDB for history retrieval (FR-30)

**Latency breakdown:** Query processing 30ms + embedding 50ms + ChromaDB search 80ms + reasoning 20ms = 180ms (NFR-1)


### 3.2 Voice Query Flow

**Step 1:** User records audio via frontend microphone → base64-encoded WAV sent to /query

**Step 2:** Speech recognition converts audio to text (90% accuracy clear audio, 79% with noise per FR-21)

**Step 3:** Follows text query flow from Step 3 onward

**Step 4:** Optional: /tts endpoint generates audio response via gTTS (adds 500ms per NFR-3, satisfies FR-26)

### 3.3 Document Upload Flow

**Step 1:** User uploads image via /upload endpoint → multipart/form-data

**Step 2:** Document checker (document_checker.py) runs pytesseract OCR with 'hin+eng' language pack (FR-22)

**Step 3:** Keyword matching detects document type (Aadhaar/PAN/ration card) per FR-23

**Step 4:** Regex patterns extract fields (name, number, DOB, gender) per FR-24

**Step 5:** Validation runs (Aadhaar checksum, date format) per FR-25

**Step 6:** Extracted demographics passed to eligibility engine → returns applicable schemes (FR-14, FR-15)

**Step 7:** Response includes {document_type, extracted_fields, validation, eligible_schemes}

**Latency:** OCR 2-3 seconds + eligibility check 100ms = 2.1-3.1 seconds (within FR-1 3-second limit)

### 3.4 Eligibility Check Flow

**Step 1:** User provides demographics via form or extracted from document

**Step 2:** Eligibility engine (eligibility.py) iterates ELIGIBILITY_RULES dictionary (FR-14)

**Step 3:** For each policy, calculate match percentage = satisfied_rules / total_rules (FR-15)

**Step 4:** Filter policies with match ≥80% per FR-15

**Step 5:** Return schemes with name, benefits, documents_required, application_link per FR-16

**Step 6:** Frontend renders as card list with "Apply Now" buttons

### 3.5 Policy Drift Analysis Flow

**Step 1:** User queries temporal change (e.g., "How did NREGA change 2019 to 2020?")

**Step 2:** Query processor extracts year range (FR-3)

**Step 3:** Drift calculator (drift.py) retrieves all documents for each year with policy filter

**Step 4:** Compute centroid embedding for each year's documents

**Step 5:** Calculate cosine distance between consecutive year centroids (FR-18)

**Step 6:** Classify drift severity: CRITICAL (>0.70), HIGH (0.45-0.70), MEDIUM (0.25-0.45), LOW (0.10-0.25) per FR-19

**Step 7:** Return drift scores, severity classifications, and major change descriptions (FR-20)

**Step 8:** Frontend renders drift visualization chart with color-coded severity

**Latency:** 800ms for multi-year analysis (NFR-2)

## 4. Design Decisions and Tradeoffs

### 4.1 Embedded vs Distributed Storage

**Decision:** Use ChromaDB file-based storage instead of distributed vector database (Qdrant, Pinecone).

**Rationale:** Target deployment environments (Jan Seva Kendras) have limited infrastructure. Single-machine deployment eliminates network configuration, container orchestration, and multi-node management. Setup time reduced from hours to minutes (NFR-20).

**Consequences:** 
- Positive: Zero-configuration deployment, offline operation (NFR-28), no container management
- Negative: Single-process limit (NFR-5: 50 concurrent users), no horizontal scaling, 10K document ceiling (NFR-6)
- Production path: Migrate to Qdrant cluster when scale exceeds 100 users (documented in OS-11)

**Requirements satisfied:** NFR-20 (3-5 minute setup), NFR-28 (offline operation), C-1 (single-machine constraint)

### 4.2 Rule-Based vs ML Eligibility

**Decision:** Implement eligibility matching using hardcoded rules rather than machine learning classification.

**Rationale:** Government eligibility criteria are explicitly documented in scheme notifications. No labeled training data exists. Rules provide legal defensibility—system can cite exact notification clause for each decision. ML model would be a black box incompatible with government accountability requirements.

**Consequences:**
- Positive: Auditable decisions, no training data required, deterministic behavior (NFR-13)
- Negative: Manual updates required when schemes change, cannot handle complex conditions (OS-7: disability rules)
- Maintenance: Rules updated quarterly by policy data curators

**Requirements satisfied:** FR-14-17 (eligibility matching), NFR-13 (deterministic), C-4 (no ML generation)


### 4.3 Retrieval-Only vs LLM Generation

**Decision:** Use template-based answer synthesis from retrieved chunks rather than LLM generation (GPT-4, Gemini).

**Rationale:** Government use requires showing exact source documents for every claim. LLMs hallucinate—GPT-4 generates plausible but incorrect budget figures 8% of the time in testing. Template synthesis guarantees reproducibility: identical query always returns identical answer. No API costs ($0.03/1K tokens for GPT-4), no rate limits, no internet dependency.

**Consequences:**
- Positive: Zero hallucination risk, deterministic responses (NFR-13), source traceability (NFR-18), offline operation (NFR-28), zero cost
- Negative: Cannot handle complex multi-hop reasoning (OS-6: multi-policy comparison), answer quality depends on template coverage, less natural language
- Fallback: Gemini API key supported but not used by default (optional enhancement)

**Requirements satisfied:** NFR-13 (deterministic), NFR-18 (source citations), NFR-28 (offline), C-4 (no LLM generation)

### 4.4 Offline Support Choices

**Decision:** Core search operates entirely offline; translation and TTS are optional online features.

**Rationale:** Jan Seva Kendras have unreliable internet connectivity. System must function without network access for core queries. Translation and TTS enhance usability but are not critical—users can query in English and read text responses.

**Consequences:**
- Positive: Reliable operation in low-connectivity environments, no API dependency for core features
- Negative: Translation quality limited to free tier (C-11: 500K chars/month), TTS requires internet (gTTS)
- Degradation: System falls back to English-only mode when translation unavailable

**Requirements satisfied:** NFR-28 (offline operation), A-2 (internet for optional features), C-11 (translation limits)

### 4.5 TinyDB vs MongoDB

**Decision:** Use TinyDB JSON file storage instead of MongoDB for user data and session history.

**Rationale:** Original design used MongoDB requiring Docker container. Field testing revealed Docker as deployment barrier—service center staff cannot manage containers. TinyDB is single JSON file with zero configuration. Adequate for <100 users (estimated deployment scale).

**Consequences:**
- Positive: Zero-configuration deployment, no container management, simple backup (copy JSON file)
- Negative: No concurrent write safety (C-2), no indexing (linear scan), no replication, file corruption risk
- Scale limit: 100 users before requiring PostgreSQL migration (OS-11)

**Requirements satisfied:** NFR-20 (3-5 minute setup), C-2 (scalability constraint), NFR-15 (persistence)

### 4.6 CPU vs GPU Embeddings

**Decision:** Use CPU-based embedding generation (all-MiniLM-L6-v2) without GPU acceleration.

**Rationale:** Target deployment hardware (Jan Seva Kendra desktops) lacks GPUs. CPU inference ensures compatibility. Model size (400MB) fits in 8GB RAM systems. 50ms embedding latency acceptable for interactive use.

**Consequences:**
- Positive: No GPU hardware requirement, compatible with commodity hardware (NFR-25: 4GB RAM minimum)
- Negative: Throughput limited to ~20 embeddings/second (vs 200+ with GPU), batch processing slow
- Scale limit: 10 queries/second (NFR-4) before CPU saturation

**Requirements satisfied:** NFR-25 (4GB RAM), NFR-26 (400MB model), C-3 (CPU-only constraint)

## 5. Failure Modes and Handling

### 5.1 Vector Search Failures

**Failure:** ChromaDB returns empty results or low similarity scores (<0.3).

**Behavior:** System removes year filter and retries with policy-only filter (FR-36). If still empty, returns generic policy description with warning flag.

**User sees:** "No exact match for requested year. Showing general information about [policy]." with confidence score <0.5.

**Logged:** Query text, filters applied, retry attempts, final result count to policypulse.log (FR-37).

**Requirements satisfied:** FR-36 (fallback behavior), FR-37 (logging), NFR-18 (confidence indication).

### 5.2 Translation Failures

**Failure:** deep-translator API unavailable, rate limit exceeded (500K chars/month), or unsupported language.

**Behavior:** System falls back to English-only mode. Query processed in English, response returned in English with language_fallback flag.

**User sees:** "Translation unavailable. Showing results in English." banner in UI.

**Logged:** Translation error, language detected, fallback applied to policypulse.log (FR-37).

**Requirements satisfied:** A-2 (internet for optional features), C-11 (translation limits).

### 5.3 OCR Failures

**Failure:** pytesseract cannot extract text (blurry image, unsupported format), or extracted text doesn't match any document pattern.

**Behavior:** System returns {document_type: "unknown", extracted_fields: {}, validation: {is_valid: false, issues: ["Could not detect document type"]}}.

**User sees:** "Unable to process document. Please upload a clear image of a supported document (Aadhaar, PAN, Ration Card)."

**Logged:** OCR confidence score, detected text length, document type detection result to policypulse.log (FR-37).

**Requirements satisfied:** FR-35 (error responses), C-12 (OCR accuracy limits).


### 5.4 Authentication Failures

**Failure:** Invalid JWT token (expired, malformed, wrong signature), or user not found.

**Behavior:** API returns 401 Unauthorized with {detail: "Invalid authentication credentials"} per FR-35.

**User sees:** Redirected to login modal. Session history unavailable until re-authentication.

**Logged:** Failed authentication attempt with timestamp, IP address (if available), and reason to policypulse.log (FR-37).

**Requirements satisfied:** FR-29 (token validation), FR-35 (error responses), NFR-21 (secure authentication).

### 5.5 Database Corruption

**Failure:** TinyDB JSON file corrupted (incomplete write, disk full), or ChromaDB SQLite database corrupted.

**Behavior:** 
- TinyDB: System creates new empty policypulse_db.json, all user data lost
- ChromaDB: System fails to start, requires manual deletion of chromadb_data/ and re-ingestion

**User sees:** 
- TinyDB: "Session history unavailable. Please log in again."
- ChromaDB: Server startup error, requires administrator intervention

**Logged:** Database corruption detected, recovery action taken to policypulse.log (FR-37).

**Mitigation:** Automated daily backup of policypulse_db.json recommended but not implemented (OS-11).

**Requirements satisfied:** NFR-14 (ChromaDB persistence), NFR-15 (TinyDB persistence), C-2 (TinyDB limitations).

### 5.6 Resource Exhaustion

**Failure:** Memory exhaustion (>8GB RAM usage), disk full (chromadb_data/ exceeds available space), or CPU saturation (>10 queries/second).

**Behavior:**
- Memory: Python process killed by OS, server restart required
- Disk: ChromaDB write operations fail, new documents cannot be ingested
- CPU: Query latency increases from 180ms to 2-3 seconds, user experience degrades

**User sees:**
- Memory/Disk: "Service temporarily unavailable. Please try again later." (502 Bad Gateway)
- CPU: Slow responses, no error message

**Logged:** Resource usage metrics (memory, disk, CPU) logged every 5 minutes to policypulse.log (FR-37).

**Mitigation:** Monitoring alerts configured for >80% memory usage, >90% disk usage, >8 queries/second sustained load (not implemented, OS-9).

**Requirements satisfied:** NFR-4 (10 queries/second limit), NFR-5 (50 concurrent users limit), NFR-6 (10K document limit).

## 6. Scalability and Deployment Considerations

### 6.1 Current Limits

**Concurrent users:** ~50 before response time degradation (NFR-5). Single-process FastAPI with file-based ChromaDB serializes requests.

**Query throughput:** ~10 queries/second (NFR-4). CPU-bound embedding generation and ChromaDB search.

**Document capacity:** ~10,000 chunks before sluggishness (NFR-6). ChromaDB SQLite backend performance degrades with large collections.

**User accounts:** ~100 before TinyDB linear scan becomes noticeable (C-2). No indexing on email field.

**Storage:** 50MB for 2,500 chunks (NFR-27). Scales linearly—10,000 chunks = ~200MB.

### 6.2 Scale-Up Requirements

**For 500 concurrent users:**
- Replace ChromaDB with Qdrant cluster (3-node minimum for HA)
- Replace TinyDB with PostgreSQL (indexed user table)
- Add Redis for session caching (reduce database load)
- Deploy FastAPI with gunicorn (8 workers) behind nginx load balancer
- Estimated cost: $150/month (DigitalOcean droplets + managed PostgreSQL)

**For 10,000 documents:**
- Migrate to Qdrant Cloud (handles 100K+ documents)
- Implement batch embedding generation (process 100 docs/batch)
- Add document versioning (track policy updates over time)
- Estimated ingestion time: 15 minutes (vs 2 minutes current)

**For 1,000 queries/second:**
- GPU-accelerated embedding server (NVIDIA T4, $0.35/hour)
- Qdrant cluster with 10+ nodes
- CDN for frontend assets (Cloudflare)
- Estimated cost: $2,000/month

**Requirements satisfied:** OS-11 (production scalability out of scope).

### 6.3 Deployment Architecture

**Current (single-machine):**
```
[User Browser] → [FastAPI :8000] → [ChromaDB ./chromadb_data/]
                      ↓
                 [TinyDB policypulse_db.json]
```

**Production (distributed):**
```
[User Browser] → [Cloudflare CDN] → [nginx Load Balancer]
                                          ↓
                                    [FastAPI Workers x8]
                                          ↓
                      ┌───────────────────┴───────────────────┐
                      ↓                                       ↓
              [Qdrant Cluster x3]                    [PostgreSQL]
                      ↓                                       ↓
              [Redis Cache]                          [Backup Storage]
```

**Requirements satisfied:** A-1 (reverse proxy for HTTPS), OS-11 (production architecture out of scope).

### 6.4 Cost Model

**Current deployment (fully offline after setup):**
- Vector search: $0/month (embedded ChromaDB)
- Embeddings: $0/month (local model)
- Translation: $0/month (free tier, 500K chars)
- TTS: $0/month (gTTS)
- Hosting: $0/month (self-hosted) or $6/month (DigitalOcean basic droplet)
- **Total: $0-6/month**

**Production deployment (500 users, 1,000 queries/day):**
- Qdrant Cloud: $50/month (1M vectors)
- PostgreSQL: $15/month (managed database)
- Redis: $10/month (managed cache)
- Compute: $40/month (4 CPU droplets)
- Translation API: $20/month (paid tier, 5M chars)
- Monitoring: $15/month (Datadog)
- **Total: $150/month**

**Requirements satisfied:** Cost transparency for government procurement evaluation.


## 7. Security and Privacy Boundaries

### 7.1 Data Processing

**Personal data processed:**
- User registration: Email address, password hash (bcrypt with salt per NFR-21)
- Chat sessions: Query text, timestamps, session IDs
- Document uploads: Extracted fields (name, document number, DOB, gender) from OCR

**Personal data NOT stored:**
- Aadhaar numbers: Extracted for validation only, discarded after response (NFR-24)
- Document images: Processed in memory, not persisted to disk (NFR-24)
- IP addresses: Not logged (privacy consideration)
- Biometric data: Not collected

**Requirements satisfied:** NFR-24 (no PII storage beyond session), NFR-21 (password hashing).

### 7.2 Trust Boundaries

**Trusted components:**
- FastAPI backend (validates all inputs per NFR-22)
- ChromaDB vector store (read-only after ingestion)
- TinyDB user database (file permissions restrict access)

**Untrusted inputs:**
- User queries (validated via Pydantic, SQL injection not applicable)
- Uploaded images (processed in isolated pytesseract subprocess)
- JWT tokens (validated signature and expiry per FR-29)

**Attack surface:**
- No SQL database (no SQL injection risk)
- No user-generated content rendering (no XSS risk)
- No file uploads to disk (no path traversal risk)
- CORS configured (currently permissive for demo, should restrict in production per NFR-23)

**Requirements satisfied:** NFR-22 (input validation), NFR-23 (CORS configuration), FR-29 (token validation).

### 7.3 Authentication Security

**Password storage:** bcrypt with automatic salt generation, cost factor 12 (NFR-21).

**Token security:** JWT with HS256 signature, 24-hour expiry, secret key from environment variable (FR-28).

**Session management:** Session IDs are UUIDs, not sequential (prevents enumeration attacks).

**Not implemented:** 
- Rate limiting (slowapi imported but not configured, OS-9)
- Account lockout after failed login attempts
- Password complexity requirements
- Two-factor authentication (OS-10: Aadhaar-based auth)

**Requirements satisfied:** FR-28 (JWT tokens), NFR-21 (password hashing), OS-9 (rate limiting out of scope).

### 7.4 Compliance Assumptions

**Data residency:** All data stored locally in India (assuming deployment on Indian servers). No data transmitted to foreign servers except optional Google Translate API (C-11).

**Right to deletion:** User accounts can be deleted by removing entry from policypulse_db.json. No data retention policy implemented.

**Audit trail:** Query logs in policypulse.log provide basic audit trail (FR-37). No tamper-proof logging (OS-9).

**Aadhaar compliance:** System does not store Aadhaar numbers (NFR-24), compliant with Aadhaar Act 2016 Section 29 (prohibition on storage by non-authorized entities).

**Not compliant with:**
- CERT-In logging requirements (6-month log retention not implemented)
- ISO 27001 (no formal security controls)
- GDPR (if deployed in EU, would require consent management)

**Requirements satisfied:** NFR-24 (no Aadhaar storage), FR-37 (basic logging), A-1 (HTTPS via reverse proxy).

### 7.5 Threat Model

**In scope:**
- Unauthorized access to user accounts (mitigated by JWT + bcrypt)
- Query injection attacks (mitigated by Pydantic validation)
- Session hijacking (mitigated by JWT expiry)

**Out of scope:**
- DDoS attacks (no rate limiting, OS-9)
- Physical access to server (assumes secure hosting environment)
- Insider threats (assumes trusted administrators)
- Supply chain attacks (dependencies not audited)

**Residual risks:**
- TinyDB file corruption or unauthorized file access (file permissions required)
- JWT secret key exposure (must be kept secure in .env file)
- Translation API key exposure (limited impact, free tier)

**Requirements satisfied:** NFR-21-23 (security controls), OS-9 (advanced security out of scope).

## 8. Traceability Matrix

### 8.1 Requirements to Design Mapping

| Requirement | Design Component | Implementation File |
|-------------|------------------|---------------------|
| FR-1 (query processing) | API Layer, Query Processor | src/api.py, src/query_processor.py |
| FR-2 (policy detection) | Query Processor | src/query_processor.py |
| FR-3 (year extraction) | Query Processor | src/query_processor.py |
| FR-4 (demographics) | Query Processor | src/query_processor.py |
| FR-5 (semantic search) | Vector Store, Embeddings | src/chromadb_setup.py, src/embeddings.py |
| FR-6 (top-k retrieval) | Vector Store | src/chromadb_setup.py |
| FR-7 (structured answers) | Reasoning Engine | src/reasoning.py |
| FR-8 (time decay) | Memory System | src/memory.py |
| FR-9 (reinforcement) | Memory System | src/memory.py |
| FR-10-12 (translation) | Translation Layer | src/translation.py |
| FR-13 (UI localization) | Frontend | frontend/src/translations.js |
| FR-14-17 (eligibility) | Eligibility Engine | src/eligibility.py |
| FR-18-20 (drift detection) | Drift Analysis | src/drift.py |
| FR-21 (voice input) | API Layer | src/api.py |
| FR-22-25 (OCR) | Document Processing | src/document_checker.py |
| FR-26 (TTS) | API Layer | src/tts.py |
| FR-27-31 (authentication) | User Database, API Layer | src/auth.py, src/api.py |
| FR-32-34 (data coverage) | Data Ingestion | cli.py, Data/ |
| FR-35-37 (error handling) | API Layer | src/api.py |
| FR-38-39 (WhatsApp) | API Layer | src/api.py, run_sms_tunnel.py |

### 8.2 Design Decisions to Requirements Mapping

| Design Decision | Requirements Satisfied | Tradeoffs Accepted |
|-----------------|------------------------|-------------------|
| ChromaDB over Qdrant | NFR-20, NFR-28, C-1 | NFR-5, NFR-6 (scale limits) |
| Rule-based eligibility | FR-14-17, NFR-13, C-4 | OS-7 (complex conditions) |
| Template synthesis | NFR-13, NFR-18, NFR-28 | OS-6 (multi-policy queries) |
| TinyDB over MongoDB | NFR-20, C-2 | OS-11 (production scalability) |
| CPU embeddings | NFR-25, NFR-26, C-3 | NFR-4 (throughput limit) |
| Offline-first | NFR-28, A-2 | C-11 (translation limits) |

---

**Document Version:** 1.0  
**Last Updated:** February 6, 2026  
**Status:** Final for Government Review
