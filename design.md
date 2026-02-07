# PolicyPulse Design Specification

## 1. Design Overview

PolicyPulse implements a retrieval-based policy information system using semantic search over a vector database. The design prioritizes deterministic behavior, source traceability, and offline operation after initial setup. The system does not use generative LLMs; all answers are synthesized from retrieved document chunks using template-based construction.

The architecture separates concerns into distinct layers: a React frontend for user interaction, a FastAPI backend for request processing, a ChromaDB vector store for semantic search, and specialized modules for translation, OCR, and eligibility matching. This separation enables independent testing and replacement of components (e.g., ChromaDB can be replaced with Qdrant without changing API contracts).

The design reflects deployment constraints for public-sector environments: no external API dependencies for core functionality, deterministic responses for auditability, explicit source citations for legal defensibility, and support for low-bandwidth scenarios (text-only mode, optional translation/TTS).

## 2. Architectural Components

### 2.1 Frontend Layer (React + Vite)

**Responsibility:** User interface, language selection, theme management, authentication state, and API communication.

**Implementation:** React 18 with Vite build system. Three context providers manage global state: LanguageContext (EN/HI/TA/TE), ThemeContext (light/dark), AuthContext (JWT tokens). Components include Sidebar (chat history), ChatArea (message display), InputBar (query submission), LoginModal (authentication), and DriftChart (policy change visualization).

**Why React over Streamlit:** Initial prototype used Streamlit (app.py in repository history). Migration to React addressed limitations: better state management without session_state workarounds, proper dark mode theming, responsive sidebar behavior, and cleaner JWT authentication integration. Streamlit's server-side rendering model caused issues with multilingual context switching.

**Data flow:** User input triggers handleSendMessage() → POST /query with {query_text, session_id, demographics, language} → response rendered in ChatArea → session stored in sidebar history.

### 2.2 API Layer (FastAPI)

**Responsibility:** HTTP endpoint handling, request validation, authentication, and orchestration of backend modules.

**Implementation:** FastAPI with Pydantic request/response models. Endpoints: /query (main search), /auth/* (signup/login/me), /history (session retrieval), /translate, /tts, /upload (OCR), /eligibility. JWT authentication via python-jose with bcrypt password hashing. User data stored in TinyDB (policypulse_db.json).

**Why FastAPI:** Async request handling, automatic OpenAPI documentation, Pydantic validation, and straightforward CORS configuration. Alternative considered was Flask, rejected due to lack of native async support and manual validation requirements.

**Why TinyDB over MongoDB:** Original design used MongoDB requiring Docker container management and connection string configuration. TinyDB eliminated deployment complexity for demonstration purposes. JSON file storage is adequate for fewer than 100 users. Production deployment would require PostgreSQL migration.

**Tradeoff:** TinyDB is single-file with no transaction isolation. Concurrent writes could corrupt data. Acceptable for demonstration; unacceptable for production.

### 2.3 Vector Store (ChromaDB)

**Responsibility:** Embedding storage, semantic search, and metadata filtering.

**Implementation:** ChromaDB 0.4.x with SQLite backend persisted to ./chromadb_data. Collection name: policy_data. Embedding dimension: 384 (all-MiniLM-L6-v2). Metadata schema per document: {policy_id, year, modality, source, access_count, decay_weight}.

**Why ChromaDB over Qdrant:** Comment from source code: "Migrated from Qdrant Jan 2024 - setup was too painful for hackathon judges. ChromaDB just works out of the box." Qdrant required Docker and network configuration. ChromaDB is pure Python with SQLite backend requiring no external services.

**Tradeoff:** ChromaDB is file-based and single-process. Estimated capacity: 10 queries/second, 50 concurrent users, 10,000 documents before performance degradation. Qdrant would support distributed deployment and higher throughput but adds operational complexity.

**Metadata filtering:** ChromaDB where clause supports exact match and $and/$or operators. System uses exact match on policy_id and year extracted from queries. Multi-policy queries not supported due to complexity of merging results from multiple where clauses.

### 2.4 Query Processing Module

**Responsibility:** Extract structured context from natural language queries including policy identifiers, year specifications, and demographic information.

**Implementation:** Keyword matching against POLICY_ALIASES dictionary (50+ entries mapping aliases like "nrega", "mgnrega", "एनआरेगा" to normalized "NREGA"). Regex patterns for year extraction: \b(20\d{2})\b, between\s+(\d{4})\s+and\s+(\d{4}), from\s+(\d{4})\s+to\s+(\d{4}). Demographic extraction via pattern matching for age, gender, occupation, location type.

**Why rules over ML:** Policy names are enumerable and aliases are documented. Training data does not exist. Rule-based approach is deterministic and debuggable. ML would require labeled query dataset and introduce non-determinism.

**Limitation:** Multi-policy queries (e.g., "compare NREGA and PM-KISAN") only detect first policy. Addressing this requires running multiple vector searches and merging results, adding latency and complexity for an edge case.

### 2.5 Reasoning Engine

**Responsibility:** Synthesize answers from retrieved document chunks using template-based construction.

**Implementation:** generate_reasoning_trace() analyzes retrieved documents for policy/modality/year distribution and scores relevance. synthesize_answer() constructs responses using templates for definitions, budget queries, eligibility, and temporal queries. Injects official application URLs from policy_urls.py mapping.

**Why templates over LLM generation:** Government deployment requires showing exactly which source document supports each claim. LLM generation introduces hallucination risk and non-determinism. Template-based synthesis ensures same query always returns same answer. Responses are auditable by tracing to source chunks.

**Confidence scoring:** (0.5 × top1_similarity) + (0.5 × result_consistency). top1_similarity is cosine similarity of best-matching document (0-1). result_consistency is fraction of top-5 results from same policy/year (1.0 = all consistent, 0.2 = highly mixed). Average confidence across test set: 0.86.

**Tradeoff:** Templates cannot handle arbitrary phrasing variations. Responses sound formulaic. LLM generation would be more natural but sacrifices determinism and traceability.

### 2.6 Eligibility Engine

**Responsibility:** Match user demographic profiles against rule-based eligibility criteria and provide exclusion reasoning.

**Implementation:** ELIGIBILITY_RULES dictionary maps policy_id to {name, description, rules, documents_required, application_link, benefits}. Rules include age_min, age_max, income_max, location_type, occupation, exclusions array. check_eligibility() iterates policies, calculates match percentage, returns policies with match ≥ 80%.

**Why rules over ML:** Government eligibility is explicitly documented in notifications. No training data exists for ML approach. Rules are auditable and legally defensible. ML predictions would lack legal grounding.

**Exclusion reasoning:** When user fails eligibility, system identifies which rule failed and cites source clause from policy metadata (e.g., "Income ₹8L exceeds limit of ₹6L under Para 5.3"). This "why not" capability does not exist in current government portals.

**Limitation:** Gender not currently in rules for most schemes. Would need to add for women-specific schemes like Beti Bachao Beti Padhao. Disability-specific rules not present in schema.

### 2.7 Memory System

**Responsibility:** Apply time decay to older documents and reinforce frequently accessed documents.

**Implementation:** Two mechanisms: (1) Time decay with coefficient 0.1 per year, minimum weight 0.3, maximum weight 1.5. weight = max(0.3, 1.0 - (current_year - doc_year) × 0.1). (2) Access reinforcement increments access_count and boosts decay_weight by 0.05 per access.

**Why both mechanisms:** Time decay prevents 2006 data from dominating "current rate" queries. Reinforcement learns which documents are actually useful based on retrieval patterns. Combined approach balances recency with relevance.

**Tradeoff:** Reinforcement creates feedback loop where popular documents become more popular. Could suppress valid but less-accessed documents. Mitigation: decay_weight ceiling of 1.5 limits reinforcement impact.

### 2.8 Translation Layer

**Responsibility:** Detect input language, translate to English for embedding, translate responses back to original language.

**Implementation:** langdetect for language detection supporting 10 Indian languages. deep-translator for translation using Google Translate free tier. Flow: Input → detect_language() → translate_text() to English → query ChromaDB → translate_response() back to original language.

**Why deep-translator:** Comment from source code: "Switched from googletrans after it broke in Jan 2024 (httpx version conflict). deep-translator is more reliable." googletrans library had dependency conflicts. deep-translator provides stable API wrapper.

**Assumption:** English translation is adequate for embedding generation across all supported languages. This assumes semantic meaning is preserved through translation. Validation: 75% accuracy on Hindi queries in test set suggests acceptable but not perfect preservation.

**Tradeoff:** Translation adds 300ms latency. Alternative would be multilingual embedding model (e.g., LaBSE) but increases model size from 400MB to 1.8GB and requires more RAM.

### 2.9 Document Processing Module

**Responsibility:** Extract text from images, detect document type, extract structured fields, validate format.

**Implementation:** pytesseract for OCR with preprocessing (grayscale conversion, contrast enhancement, sharpening). detect_document_type() matches keywords for Aadhaar, PAN, ration card. extract_fields() uses regex for name, document number, DOB, gender. validate_document() checks Aadhaar Verhoeff checksum.

**Why pytesseract:** Open-source, works offline, supports Indian language packs. Alternative was Google Cloud Vision API, rejected due to cost and online dependency.

**Limitation from source code:** "OCR quality is... variable. Hindi works ok, Tamil is rough. might need to add tesseract language packs per deployment. NOTE: we tested with caste certificates too but accuracy was <60% would need more training data to add."

**Accuracy:** 94% on printed Aadhaar cards, 76% on income certificates, 56% on handwritten documents. Preprocessing improves accuracy on noisy/blurry photos but cannot compensate for poor handwriting.

### 2.10 Embedding Model

**Responsibility:** Generate 384-dimensional vector representations of text for semantic search.

**Implementation:** sentence-transformers all-MiniLM-L6-v2 model. CPU-compatible, no GPU required. Model size: ~400MB. Loaded once at startup and cached in memory.

**Why all-MiniLM-L6-v2:** Balance of speed, size, and accuracy. Alternatives considered: (1) all-mpnet-base-v2 (768-dim, better accuracy, 2x slower), (2) multilingual models (LaBSE, 1.8GB, 4x slower). all-MiniLM-L6-v2 meets latency requirements on reference hardware.

**Tradeoff:** 384 dimensions provide less semantic nuance than 768-dim models. Acceptable for policy retrieval where queries are relatively simple. Would need larger model for complex reasoning tasks.

## 3. Data Flow

### 3.1 Text Query Flow

1. Frontend sends POST /query with {query_text, session_id, language}
2. API validates request via Pydantic schema
3. Query processor extracts policy_id, years, demographics
4. If language != 'en', translate query to English
5. Generate embedding for translated query
6. Build ChromaDB where filter from extracted context
7. Query ChromaDB with embedding and filter, return top-5 results
8. Apply time decay and access reinforcement to results
9. Reasoning engine synthesizes answer from retrieved chunks
10. If language != 'en', translate answer back to original language
11. Store query and response in chat history (TinyDB)
12. Return {final_answer, confidence_score, sources, session_id}

**Latency breakdown (reference hardware):**
- Query processing: 20ms
- Translation (if needed): 300ms
- Embedding generation: 50ms
- ChromaDB search: 80ms
- Answer synthesis: 30ms
- Total: ~180ms (text), ~480ms (with translation)

### 3.2 Voice Query Flow

1. Frontend captures audio via microphone, sends as WAV/MP3
2. API receives audio file
3. Speech recognition converts audio to text (90% accuracy clear audio, 79% with noise)
4. Proceed with text query flow from step 2
5. Optionally generate TTS audio response via gTTS
6. Return text response + audio URL

**Additional latency:** Speech recognition adds ~500ms. TTS adds ~500ms if requested.

### 3.3 Document Upload Flow

1. Frontend sends image file via POST /upload
2. API receives image, applies preprocessing (grayscale, contrast, sharpening)
3. pytesseract extracts text with language packs (hin+eng)
4. detect_document_type() matches keywords (aadhaar, pan, ration)
5. extract_fields() applies regex patterns for structured data
6. validate_document() checks format (e.g., Aadhaar Verhoeff checksum)
7. If valid, run eligibility check with extracted demographics
8. Return {document_type, extracted_fields, validation, eligible_schemes}

**Latency:** OCR processing takes 2-4 seconds depending on image size and quality.

### 3.4 Eligibility Check Flow

1. Receive user profile {age, gender, occupation, location_type, category, income}
2. Iterate ELIGIBILITY_RULES dictionary (50 schemes with full rules, 80+ with basic rules)
3. For each policy, compare profile against rules
4. Calculate match_score = matched_rules / total_rules
5. If match_score ≥ 0.8, add to eligible list
6. If match_score < 0.8, identify failed rules and add to excluded list with reasons
7. Return {eligible: [{policy, benefits, documents, link}], excluded: [{policy, reason, source_clause}]}

**Latency:** Rule matching is CPU-bound, ~50ms for 130 policies.

### 3.5 Drift Analysis Flow

1. Detect temporal query pattern (e.g., "how did X change", "between 2019 and 2020")
2. Extract policy_id and year range
3. For each year in range:
   - Retrieve all documents with {policy_id, year}
   - Generate embeddings for all documents
   - Calculate centroid (mean embedding)
4. Compute cosine distance between consecutive year centroids
5. Classify severity: CRITICAL (>0.70), HIGH (0.45-0.70), MEDIUM (0.25-0.45), LOW (0.10-0.25)
6. Return {drift_scores: [{year_from, year_to, score, severity}], visualization_data}

**Latency:** Drift analysis requires multiple embedding operations, ~800ms for 5-year range.

## 4. Design Decisions and Tradeoffs

### 4.1 Retrieval-Only vs LLM Generation

**Decision:** Use retrieval + template synthesis, not LLM generation.

**Rationale:** Government deployment requires deterministic behavior (same query → same answer), source traceability (every fact cites document), and no hallucination risk. LLM generation would provide more natural language but sacrifices these properties.

**Consequence:** Responses sound formulaic. Cannot handle arbitrary phrasing variations. Acceptable tradeoff for legal defensibility.

### 4.2 Embedded vs Distributed Storage

**Decision:** Use ChromaDB file-based storage, not distributed Qdrant.

**Rationale:** Demonstration deployment targets single-machine setup with minimal operational complexity. ChromaDB requires no external services, no Docker, no network configuration.

**Consequence:** Limited to ~10 queries/second, ~50 concurrent users, ~10,000 documents. Production deployment would require Qdrant migration.

### 4.3 Rule-Based vs ML Eligibility

**Decision:** Use rule-based eligibility matching, not ML classification.

**Rationale:** Government eligibility is explicitly documented in notifications. No training data exists. Rules are auditable and legally defensible. ML predictions would lack legal grounding.

**Consequence:** Rules must be manually curated from policy documents. 50 schemes fully annotated, 80+ with basic rules. Scaling requires continued manual effort.

### 4.4 Translation vs Multilingual Embeddings

**Decision:** Translate to English for embedding, not use multilingual embedding model.

**Rationale:** all-MiniLM-L6-v2 (400MB, 384-dim) fits in 8GB RAM with headroom. Multilingual models (LaBSE, 1.8GB, 768-dim) would require 16GB RAM and 4x slower inference.

**Consequence:** Translation adds 300ms latency. Semantic meaning may be lost in translation (75% accuracy on Hindi queries). Acceptable for demonstration; production might justify multilingual model.

### 4.5 Offline Support

**Decision:** Core search works fully offline after data ingestion. Translation and TTS require internet.

**Rationale:** Jan Seva Kendras may have unreliable connectivity. Offline capability ensures basic functionality always available.

**Consequence:** Translation and TTS degrade gracefully when offline. System returns English responses and skips audio generation.

## 5. Failure Modes and Handling

### 5.1 No Matching Documents

**Failure:** Query filter (policy + year) returns zero results.

**Behavior:** Remove year constraint, query by policy only. If still zero, return "No data available for [policy]."

**User sees:** "PM-AWAS was launched in 2015. No data available for 2008 as the scheme did not exist then. Available data: 2015-2025."

**Logged:** Warning level with query text and filter.

### 5.2 Translation Service Unavailable

**Failure:** deep-translator cannot reach Google Translate API (network error, rate limit).

**Behavior:** Skip translation, return English response with warning.

**User sees:** Response in English with message "Translation unavailable, showing English response."

**Logged:** Error level with exception details.

### 5.3 OCR Extraction Failure

**Failure:** pytesseract returns empty string or unrecognizable text.

**Behavior:** Return validation error with extracted text for debugging.

**User sees:** "Could not extract text from image. Please ensure image is clear and well-lit."

**Logged:** Warning level with image metadata (size, format).

### 5.4 ChromaDB Corruption

**Failure:** SQLite database corruption (disk full, power loss during write).

**Behavior:** ChromaDB raises sqlite3.DatabaseError. API returns HTTP 500.

**User sees:** "System error, please try again later."

**Logged:** Critical level with stack trace.

**Recovery:** Administrator must delete chromadb_data/ and run cli.py ingest-all to rebuild.

### 5.5 JWT Token Expiry

**Failure:** User makes authenticated request with expired token.

**Behavior:** API returns HTTP 401 Unauthorized.

**User sees:** Frontend redirects to login modal.

**Logged:** Info level (expected behavior, not error).

### 5.6 Ambiguous Query

**Failure:** Query does not match any policy alias and contains no year.

**Behavior:** Query all policies without filter, return best match with low confidence.

**User sees:** Response with MEDIUM or LOW confidence badge and suggestion to be more specific.

**Logged:** Debug level with query text.

## 6. Scalability and Deployment Considerations

### 6.1 Current Limits

- ChromaDB: Single-process, file-based. Estimated 10 queries/second, 50 concurrent users.
- TinyDB: Single-file JSON. No transaction isolation. Suitable for <100 users.
- Embedding model: Loaded in memory (~400MB). Single instance per process.
- Disk: ~50MB for ChromaDB, ~2MB for TinyDB. Grows with usage.

### 6.2 Scaling to 500+ Users

**Required changes:**

1. **Vector store:** Migrate ChromaDB to Qdrant cluster. Qdrant supports distributed deployment, horizontal scaling, and higher throughput. Estimated cost: $50/month for managed Qdrant Cloud.

2. **User database:** Migrate TinyDB to PostgreSQL. Add connection pooling (e.g., pgbouncer). Estimated cost: $15/month for managed PostgreSQL.

3. **API layer:** Deploy FastAPI with gunicorn workers (4-8 workers). Add Redis for session caching. Estimated cost: $20/month for Redis.

4. **Load balancing:** Add nginx reverse proxy for HTTPS termination and load distribution. Estimated cost: included in compute.

5. **Compute:** Upgrade from single DigitalOcean droplet ($12/month) to 2-4 instances ($48/month).

**Total estimated cost for 500 users:** ~$150/month.

### 6.3 Scaling to 10,000+ Users

**Additional changes:**

1. **Embedding service:** Separate embedding generation into dedicated service with GPU acceleration. Reduces latency from 50ms to 10ms. Estimated cost: $100/month for GPU instance.

2. **CDN:** Serve frontend static assets via CDN (Cloudflare). Reduces bandwidth costs.

3. **Monitoring:** Add Prometheus + Grafana for metrics. Add Sentry for error tracking.

4. **Caching:** Add Redis cache for frequent queries (e.g., "What is NREGA?"). Cache hit rate estimated 30-40%.

**Total estimated cost for 10,000 users:** ~$500/month.

### 6.4 Cost Implications

**Current (demonstration):**
- DigitalOcean droplet: $12/month
- Translation: Free tier (500K chars/month)
- TTS: Free (gTTS)
- Total: $12/month

**Production (500 users):** ~$150/month (12.5x increase)

**Production (10,000 users):** ~$500/month (41.7x increase)

**Cost per user:** $0.024/month (demonstration), $0.30/month (500 users), $0.05/month (10,000 users). Economies of scale reduce per-user cost.

## 7. Security and Privacy Boundaries

### 7.1 Personal Data Processing

**Data collected:**
- User registration: email, password hash (bcrypt)
- Chat history: query text, response text, timestamp, session_id
- Document uploads: OCR text, extracted fields (name, document number, DOB, gender)

**Data NOT stored:**
- Uploaded images (processed in memory, discarded after OCR)
- Voice recordings (processed in memory, discarded after speech recognition)
- Aadhaar numbers (extracted for validation, not persisted)

### 7.2 Data Retention

**User data:** Stored indefinitely in policypulse_db.json. No automatic deletion.

**Chat history:** Stored indefinitely per user. No automatic deletion.

**Logs:** Rotated daily, retained for 7 days in logs/policypulse.log.

**Production requirement:** Implement data retention policy compliant with IT Act 2000 and Personal Data Protection Bill. Suggested: 90-day retention for chat history, 30-day for logs.

### 7.3 Trust Boundaries

**Trusted:**
- Policy data in Data/ directory (manually curated from official sources)
- Eligibility rules in eligibility.py (manually encoded from notifications)
- Authority metadata (notification numbers, gazette URLs)

**Untrusted:**
- User input (query text, uploaded images)
- Translation API responses (could be incorrect or unavailable)
- OCR output (could be incorrect due to image quality)

**Validation:** User input validated via Pydantic schemas. OCR output validated via checksums (Aadhaar Verhoeff). Translation failures handled gracefully.

### 7.4 Authentication and Authorization

**Authentication:** JWT tokens with configurable expiry (default 24 hours). Tokens signed with SECRET_KEY from environment.

**Authorization:** No role-based access control. All authenticated users have same permissions.

**Production requirement:** Add role-based access control (citizen, staff, admin). Staff role can view all user queries for quality monitoring. Admin role can ingest new data.

### 7.5 Compliance Assumptions

**Assumption 1:** System provides informational responses only, not legal advice. Disclaimer required in UI.

**Assumption 2:** Eligibility determinations are guidance, not official certification. Users must verify with official portals.

**Assumption 3:** Policy data accuracy is best-effort. System displays data_as_of and last_verified dates for transparency.

**Assumption 4:** No PII is shared with third parties. Translation API receives query text (may contain PII) but not user identity.

**Production requirement:** Legal review of disclaimer language. Privacy policy compliant with IT Act 2000. Terms of service clarifying system limitations.

## 8. Traceability Matrix

### 8.1 Requirements to Design Mapping

| Requirement | Design Component | Implementation File |
|-------------|------------------|---------------------|
| FR-1 to FR-5 | Query Processing Module | src/query_processor.py |
| FR-6 to FR-9 | Translation Layer | src/translation.py, frontend/src/translations.js |
| FR-10 to FR-14 | Document Processing Module | src/document_checker.py |
| FR-15 to FR-19 | Eligibility Engine | src/eligibility.py |
| FR-20 to FR-23 | Memory System (drift analysis) | src/drift.py |
| FR-24 to FR-29 | Vector Store | src/chromadb_setup.py |
| FR-30 to FR-34 | Reasoning Engine | src/reasoning.py |
| FR-35 to FR-38 | API Layer (auth) | src/auth.py, src/api.py |
| FR-39 to FR-42 | Data Ingestion | cli.py, src/data_ingestion.py |
| FR-43 to FR-46 | API Layer (error handling) | src/api.py |

### 8.2 Design Decisions to Requirements

| Design Decision | Satisfies Requirements | Rationale |
|-----------------|------------------------|-----------|
| Template-based synthesis | FR-30, NFR-6, NFR-7 | Deterministic responses, source traceability |
| ChromaDB file-based | NFR-7, C-1 | Persistence, single-process constraint |
| Rule-based eligibility | FR-15 to FR-19 | Legal defensibility, no training data |
| Translation layer | FR-6 to FR-9, NFR-12 | Multilingual support without multilingual embeddings |
| Time decay + reinforcement | FR-28, FR-29 | Balance recency with relevance |
| Pydantic validation | NFR-20, FR-46 | Input validation, error handling |

## 9. Known Limitations

### 9.1 Architectural Limitations

**L-1:** Single-policy queries only. Multi-policy comparison requires multiple vector searches and result merging not implemented.

**L-2:** ChromaDB single-process limit. Concurrent writes could cause corruption. Acceptable for demonstration; unacceptable for production.

**L-3:** TinyDB lacks transaction isolation. Concurrent writes could corrupt user database.

**L-4:** No caching layer. Frequent queries (e.g., "What is NREGA?") re-compute embeddings and search every time.

### 9.2 Data Limitations

**L-5:** Policy data manually curated. No automated scraping from ministry websites. Data freshness depends on manual updates.

**L-6:** Authority metadata (notification numbers, supersession chains) manually curated for 50 schemes. Remaining 80+ schemes lack full metadata.

**L-7:** Clause-level change tracking manually annotated for 4 schemes. Automated Gazette PDF parsing not implemented.

**L-8:** Gender not in eligibility rules for most schemes. Disability-specific rules not present.

### 9.3 Functional Limitations

**L-9:** Handwritten OCR accuracy <60%. Unusable for handwritten forms.

**L-10:** Translation quality varies by language. Tamil and Telugu less accurate than Hindi.

**L-11:** Modality detection weak. Query "how did NREGA change" often returns budget data instead of temporal data.

**L-12:** No audit logging. Cannot trace who accessed what data when.

**L-13:** No rate limiting. Vulnerable to abuse.

### 9.4 Deployment Limitations

**L-14:** HTTP only (no HTTPS). Assumes reverse proxy handles TLS termination.

**L-15:** Voice input requires browser flag on remote HTTP. Works on localhost without configuration.

**L-16:** SMS backend implemented but paused pending A2P 10DLC registration (3-week regulatory process).

**L-17:** USSD interface not implemented. Requires direct telecom integration.
