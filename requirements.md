# PolicyPulse Requirements Specification

## 1. Purpose and Scope

PolicyPulse is a policy information retrieval and eligibility determination system for Indian government schemes. The system addresses documented failures in citizen access to policy information at Jan Seva Kendras and similar public service centers, where staff lack current policy knowledge and citizens cannot determine eligibility or trace policy changes. The system provides semantic search over 130+ government schemes with multilingual support, eligibility determination, and policy change detection.

## 2. Stakeholders

**Citizens**: Primary end users seeking policy information, eligibility determination, and application guidance. Includes farmers, students, elderly, and rural populations with varying literacy and language capabilities.

**Jan Seva Kendra Staff**: Government service center operators who use the system to answer citizen queries and verify eligibility.

**System Administrators**: Personnel responsible for data ingestion, system deployment, and maintenance of the vector database and policy corpus.

## 3. Functional Requirements

### 3.1 Query Processing

FR-1: The system shall accept text queries in natural language and return policy information with source citations.

FR-2: The system shall detect policy identifiers from queries using keyword matching against a predefined alias dictionary containing 50+ policy names in English and Hindi.

FR-3: The system shall extract year specifications from queries using regex patterns matching 4-digit years and year ranges (e.g., "2023", "between 2019 and 2021").

FR-4: The system shall extract demographic information from queries including age, gender, occupation, location type, and category using pattern matching.

FR-5: The system shall return structured responses containing final answer text, confidence score (0-1 range), source documents with policy ID, year, and modality, and reasoning steps.

### 3.2 Language Support

FR-6: The system shall detect input language using the langdetect library supporting Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, and English.

FR-7: The system shall translate non-English queries to English for embedding generation and vector search.

FR-8: The system shall translate English responses back to the detected input language using deep-translator.

FR-9: The system shall provide a user interface with full localization in English, Hindi, Tamil, and Telugu including navigation elements, button labels, and system messages.

### 3.3 Multimodal Input

FR-10: The system shall accept voice input in WAV or MP3 format and convert to text using speech recognition.

FR-11: The system shall accept image uploads and extract text using pytesseract OCR with preprocessing (grayscale conversion, contrast enhancement, sharpening).

FR-12: The system shall detect document types from OCR text by matching keywords for Aadhaar cards, PAN cards, and ration cards.

FR-13: The system shall extract structured fields from recognized documents including name, document number, date of birth, and gender using regex patterns.

FR-14: The system shall validate extracted Aadhaar numbers using Verhoeff checksum algorithm.

### 3.4 Eligibility Determination

FR-15: The system shall match user demographic profiles against rule-based eligibility criteria for 50 fully annotated schemes.

FR-16: The system shall return eligible schemes where user profile matches at least 80% of defined eligibility rules.

FR-17: The system shall return excluded schemes with specific exclusion reasons citing the source clause from policy metadata (e.g., "Income ₹8L exceeds limit of ₹6L under Para 5.3").

FR-18: The system shall provide required documents list and official application URLs for each eligible scheme.

FR-19: The system shall exclude draft policies from eligibility determination and mark them with visual indicators when shown for informational queries.

### 3.5 Policy Change Detection

FR-20: The system shall compute semantic drift between consecutive years by calculating cosine distance between year-specific document centroid embeddings.

FR-21: The system shall classify drift severity as CRITICAL (>0.70), HIGH (0.45-0.70), MEDIUM (0.25-0.45), or LOW (0.10-0.25).

FR-22: The system shall display drift analysis results with year-over-year comparison when temporal queries are detected.

FR-23: The system shall provide supersession chain information showing which notification replaced prior policy versions for 50 schemes with documented amendments.

### 3.6 Vector Search and Retrieval

FR-24: The system shall generate 384-dimensional embeddings using sentence-transformers all-MiniLM-L6-v2 model.

FR-25: The system shall store document embeddings in ChromaDB with metadata including policy_id, year, modality (budget/news/temporal), source, access_count, and decay_weight.

FR-26: The system shall perform semantic search returning top-N results ranked by cosine similarity.

FR-27: The system shall apply metadata filters to restrict search by policy_id, year, or modality when extracted from query context.

FR-28: The system shall apply time decay weighting with coefficient 0.1 per year, minimum weight 0.3, maximum weight 1.5.

FR-29: The system shall apply access reinforcement by incrementing access_count and boosting decay_weight by 0.05 per access.

### 3.7 Answer Synthesis

FR-30: The system shall synthesize answers using template-based construction from retrieved document chunks, not generative LLM output.

FR-31: The system shall compute confidence scores as (0.5 × top1_similarity) + (0.5 × result_consistency) where result_consistency is the fraction of top-5 results from the same policy and year.

FR-32: The system shall display confidence badges as HIGH (≥0.8), MEDIUM (0.5-0.8), or LOW (<0.5).

FR-33: The system shall include effective_date, data_as_of, and last_verified timestamps in responses for 50 schemes with verified metadata.

FR-34: The system shall inject official application URLs from policy_urls.py mapping for recognized policies.

### 3.8 User Authentication and Session Management

FR-35: The system shall support user registration with email and password stored in TinyDB with bcrypt hashing.

FR-36: The system shall generate JWT tokens on successful login with configurable expiry.

FR-37: The system shall maintain chat session history per user with session_id, timestamp, and message content.

FR-38: The system shall allow retrieval of past sessions and messages via authenticated API endpoints.

### 3.9 Data Ingestion

FR-39: The system shall ingest policy data from CSV files in Data/ directory containing budget, news, and temporal text data.

FR-40: The system shall parse CSV files with columns for policy_id, year, content, and source.

FR-41: The system shall generate embeddings for ingested documents and store in ChromaDB with metadata.

FR-42: The system shall provide CLI commands for bulk ingestion (ingest-all) and collection statistics.

### 3.10 Error Handling

FR-43: The system shall return fallback responses when no documents match the query filter, removing year constraints and querying by policy only.

FR-44: The system shall return warning messages when requested year data does not exist (e.g., "PM-AWAS launched in 2015, no data for 2008").

FR-45: The system shall log errors to logs/policypulse.log with timestamp, level, and stack trace.

FR-46: The system shall return HTTP 400 for invalid request formats and HTTP 500 for internal processing errors.

## 4. Non-Functional Requirements

### 4.1 Performance

NFR-1: The system shall return responses for simple text queries within 500ms on Intel i5, 8GB RAM, SSD hardware.

NFR-2: The system shall complete drift analysis queries within 1000ms.

NFR-3: The system shall add translation overhead of maximum 300ms for non-English queries.

NFR-4: The system shall support approximately 10 queries per second on reference hardware.

NFR-5: The system shall support approximately 50 concurrent users on reference hardware.

### 4.2 Reliability

NFR-6: The system shall provide deterministic responses where identical queries return identical answers (no LLM generation variability).

NFR-7: The system shall persist ChromaDB data to disk at ./chromadb_data with automatic recovery on restart.

NFR-8: The system shall persist user data to policypulse_db.json with atomic writes.

### 4.3 Usability

NFR-9: The system shall provide a web interface accessible via standard browsers without plugin requirements.

NFR-10: The system shall support voice input on localhost without additional configuration; remote HTTP deployments require browser flag configuration.

NFR-11: The system shall provide dark mode and light mode themes with user preference persistence.

NFR-12: The system shall display policy information in user's selected language within the UI.

### 4.4 Accuracy

NFR-13: The system shall achieve 92% year accuracy (correct year in top-1 result for year-specific queries) on the 64-query test set.

NFR-14: The system shall achieve 78% overall accuracy (correct year and modality) on the 64-query test set.

NFR-15: The system shall achieve 80% precision on CRITICAL drift threshold classification validated against documented policy changes.

NFR-16: The system shall achieve 90% speech recognition accuracy on clear audio and 79% with background noise.

NFR-17: The system shall achieve 94% OCR accuracy on printed Aadhaar cards, 76% on income certificates, and 56% on handwritten documents.

### 4.5 Security

NFR-18: The system shall hash passwords using bcrypt before storage.

NFR-19: The system shall validate JWT tokens on protected endpoints.

NFR-20: The system shall validate Pydantic request schemas on all API endpoints.

NFR-21: The system shall configure CORS headers (currently permissive for demonstration purposes).

### 4.6 Data Coverage

NFR-22: The system shall provide retrieval capability for 130+ government schemes.

NFR-23: The system shall provide full eligibility rules and authority metadata for 50 schemes.

NFR-24: The system shall provide basic eligibility rules for 80+ additional schemes pending full annotation.

NFR-25: The system shall index approximately 2,500+ document chunks across 223 data files.

## 5. Constraints and Assumptions

### 5.1 Technical Constraints

C-1: The system uses ChromaDB file-based storage limited to single-process access.

C-2: The system uses TinyDB JSON file storage suitable for fewer than 100 users.

C-3: The system requires Python 3.11 runtime environment.

C-4: The system requires 4GB minimum RAM, 8GB recommended.

C-5: The system requires 2GB disk space for dependencies and data.

C-6: The system uses CPU-only embedding model (all-MiniLM-L6-v2) without GPU acceleration.

### 5.2 Data Constraints

C-7: Policy data is ingested once at setup and not updated automatically from ministry websites.

C-8: Data freshness depends on manual curation; data_as_of dates reflect last manual update.

C-9: Authority metadata (notification numbers, gazette URLs, supersession chains) is manually curated for 50 schemes.

C-10: Clause-level change tracking is manually annotated for 4 schemes (NREGA, PM-KISAN, RTI, Ayushman Bharat).

### 5.3 Operational Assumptions

A-1: The system assumes deployment behind a reverse proxy handling HTTPS termination.

A-2: The system assumes Tesseract OCR is installed for document processing features; core search functions without it.

A-3: The system assumes internet connectivity for translation and TTS features; core search works offline.

A-4: The system assumes English translation is adequate for embedding generation across all supported languages.

### 5.4 Legal and Regulatory Assumptions

A-5: The system assumes Central Government scheme hierarchy; State-level schemes and Concurrent List conflicts require manual curation.

A-6: The system assumes notification supersession metadata is legally accurate when provided.

A-7: The system assumes eligibility rules encoded in JSON schema match official policy documents.

A-8: The system does not provide legal advice; responses are informational only.

## 6. Out-of-Scope Items

The following capabilities are explicitly not implemented:

OS-1: LLM-based answer generation (system uses retrieval + template synthesis only).

OS-2: Real-time policy scraping from ministry websites (data is ingested once at setup).

OS-3: Application submission or enrollment flows (system provides links to official portals).

OS-4: Live SMS delivery to US phone numbers (backend code implemented but paused pending A2P 10DLC registration).

OS-5: USSD interface for feature phones (requires direct telecom integration not available).

OS-6: Automated Gazette PDF parsing for clause extraction (requires OCR and legal document parsing not implemented).

OS-7: Multi-policy comparison queries (system handles single policy per query).

OS-8: Disability-specific eligibility rules (not present in current rule schema).

OS-9: State-level scheme hierarchies and conflict resolution (Central Government schemes only).

OS-10: Audit logging and rate limiting (imported but not wired in current implementation).

OS-11: Aadhaar-based authentication (document OCR only, no eKYC integration).

OS-12: Grievance submission or RTI application filing (guidance provided, submission not handled).
