# Architecture Overview

## System Design

PolicyPulse implements a **vector-centric distributed architecture** optimized for policy analysis:

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                               │
│  (API Clients, CLI, Streamlit Frontend, Analysis Tools)         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI SERVICE                              │
│  ┌────────────────┐  ┌─────────────┐  ┌────────────────────┐   │
│  │ Query Endpoint │  │ Drift Anal. │  │ Recommendations    │   │
│  └────────────────┘  └─────────────┘  └────────────────────┘   │
│  ┌────────────────┐  ┌─────────────┐  ┌────────────────────┐   │
│  │ Memory Mgmt    │  │ Ingest Doc  │  │ Stats & Health     │   │
│  └────────────────┘  └─────────────┘  └────────────────────┘   │
└──────┬──────────────────────┬──────────────────────┬────────────┘
       │                      │                      │
       ▼                      ▼                      ▼
┌────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Reasoning      │   │ Embedding        │   │ Memory           │
│ Engine         │   │ Models           │   │ Management       │
├────────────────┤   ├──────────────────┤   ├──────────────────┤
│ • Intent Parse │   │ • SentenceXForm  │   │ • Time Decay     │
│ • Year Extract │   │  (all-MiniLM)    │   │ • Access Count   │
│ • Modal Filter │   │ • Twitter RoBERTa│   │ • Consolidate    │
│ • Answer Synth │   │  (sentiment)     │   │                  │
│ • Confidence   │   │                  │   │                  │
└────────────────┘   └──────────────────┘   └──────────────────┘
       │                      │                      │
       └──────────┬───────────┴──────────┬───────────┘
                  ▼                      ▼
        ┌─────────────────────────────────────────────┐
        │       QDRANT VECTOR DATABASE                │
        │  ┌─────────────────────────────────────┐    │
        │  │  policy_data collection             │    │
        │  │  ├─ 10 policies                     │    │
        │  │  ├─ 3 modalities (T, B, N)         │    │
        │  │  ├─ 384-D vectors (cosine)         │    │
        │  │  └─ Rich metadata payloads         │    │
        │  └─────────────────────────────────────┘    │
        │  ┌─────────────────────────────────────┐    │
        │  │  policy_memory collection           │    │
        │  │  (session tracking, decay history)  │    │
        │  └─────────────────────────────────────┘    │
        └─────────────────────────────────────────────┘
                         │
                         ▼
        ┌─────────────────────────────────────────────┐
        │    PERSISTENT DATA LAYER                    │
        │  ├─ qdrant_storage/ (vector DB state)      │
        │  ├─ Data/ (CSV/TXT source files)           │
        │  └─ logs/ (API activity)                   │
        └─────────────────────────────────────────────┘
```

## Data Flow

### 1. Ingestion Pipeline

```
Source Files (CSV/TXT)
    │
    ▼
┌─────────────────────┐
│ CLI Ingestion       │
│ (cli.py ingest-all) │
└─────────────────────┘
    │
    ├─ Budget CSV → Parse → Create 3 text variants
    ├─ News CSV   → Parse → Extract headline + summary
    └─ Temporal TXT → Split → Extract year sections
    │
    ▼
┌─────────────────────┐
│ Embedding Engine    │
│ (SentenceTransform) │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Sentiment Analysis  │
│ (Twitter-RoBERTa)   │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Create PointStruct  │
│ (ID, Vector,        │
│  Payload Metadata)  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Upsert to Qdrant    │
│ (policy_data)       │
└─────────────────────┘
    │
    ▼
[Vector DB Ready]
```

### 2. Query Processing Pipeline

```
User Query
    │
    ▼
┌──────────────────────────────────────────┐
│ Reasoning Trace Generation               │
│ (src/reasoning.py)                       │
└──────────────────────────────────────────┘
    │
    ├─ Step 1: Embed query (384-D vector)
    │    └─ Query vector = SentenceTransform(question)
    │
    ├─ Step 2: Detect year (regex: 20\d{2})
    │    └─ If found: add year filter to search
    │
    ├─ Step 3: Detect intent
    │    ├─ Keywords: ["budget", "allocation", "spending"]
    │    │   └─ Filter: modality = "budget"
    │    ├─ Keywords: ["intent", "purpose", "launched"]
    │    │   └─ Filter: modality = "temporal"
    │    └─ Keywords: ["news", "media", "discourse"]
    │       └─ Filter: modality = "news"
    │
    ├─ Step 4: Vector search
    │    ├─ Query vector + filters → Qdrant
    │    └─ Return: top_k results with scores
    │
    ├─ Step 5: Memory reinforcement
    │    ├─ Increment access_count
    │    └─ Boost decay_weight
    │
    ├─ Step 6: Answer synthesis
    │    ├─ Group by modality (temporal, budget, news)
    │    └─ Format: multi-section response
    │
    └─ Step 7: Confidence calculation
       └─ Mean of top-3 similarity scores
    │
    ▼
Reasoning Trace Response
    ├─ steps (7 processing steps)
    ├─ retrieved_points (ranked results)
    ├─ final_answer (synthesized response)
    └─ confidence (0-1 score)
```

### 3. Drift Analysis Pipeline

```
Drift Request (policy_id, modality, year_range)
    │
    ▼
┌──────────────────────────────────────────┐
│ Drift Timeline Computation               │
│ (src/drift.py)                           │
└──────────────────────────────────────────┘
    │
    ├─ Retrieve all embeddings by year
    │    └─ Scroll Qdrant: filter by policy + modality
    │
    ├─ Compute year centroids
    │    ├─ For each year: mean(all vectors in year)
    │    └─ Normalize by L2 norm
    │
    ├─ Calculate cosine similarity
    │    ├─ similarity = dot(centroid_t1, centroid_t2)
    │    └─ clip(-1.0, 1.0)
    │
    ├─ Convert to drift score
    │    └─ drift = 1.0 - similarity
    │
    ├─ Classify severity
    │    ├─ drift > 0.70 → CRITICAL
    │    ├─ drift > 0.45 → HIGH
    │    ├─ drift > 0.25 → MEDIUM
    │    ├─ drift > 0.10 → LOW
    │    └─ drift ≤ 0.10 → MINIMAL
    │
    └─ Return timeline
       └─ [from_year, to_year, drift_score, severity]
```

## Core Components

### 1. Embeddings Module (`src/embeddings.py`)

**Purpose**: Text vectorization and sentiment analysis

```
Input: "NREGA allocated Rs 50,000 crore in 2023"
    │
    ├─ Embedding:
    │  └─ all-MiniLM-L6-v2 → 384-D vector
    │
    └─ Sentiment:
       └─ twitter-roberta-base-sentiment → [neg, neu, pos]
```

**Key Features**:
- Lazy loading of models
- Batch processing support
- CUDA/CPU device selection
- Error handling and logging

### 2. Vector Database (`src/qdrant_setup.py`)

**Purpose**: Vector storage and semantic search

**Collections**:
- `policy_data`: Main collection for policy documents
- `policy_memory`: Secondary collection for session state

**Indexes**:
- `policy_id` (KEYWORD): Filter by policy
- `year` (KEYWORD): Filter by year
- `modality` (KEYWORD): Filter by data type

**Vector Config**:
- Size: 384 dimensions
- Distance: COSINE similarity
- Maximum capacity: ~1M vectors (configurable)

### 3. Reasoning Engine (`src/reasoning.py`)

**Purpose**: Multi-step query understanding and answering

**Pipeline**:
1. Query embedding
2. Intent detection (policy/budget/news)
3. Year extraction (if mentioned)
4. Vector search with filters
5. Result ranking by score
6. Memory reinforcement
7. Multi-modal synthesis

**Output**:
```json
{
  "query": "user question",
  "steps": [7 processing steps],
  "retrieved_points": [ranked results],
  "final_answer": "synthesized response",
  "confidence": 0.85
}
```

### 4. Memory Management (`src/memory.py`)

**Purpose**: Adaptive memory with learning and forgetting

**Mechanisms**:

| Mechanism | Purpose | Formula |
|-----------|---------|---------|
| **Time Decay** | Forget old data | `weight = exp(-0.1 * age_years)` |
| **Access Boost** | Remember used data | `weight *= (1 + 0.02 * access_count)` |
| **Consolidation** | Merge duplicates | Cosine similarity ≥ 0.95 |

**Payload Fields**:
```python
{
  "decay_weight": 0.85,      # Current relevance
  "access_count": 5,          # Times accessed
  "age_years": 2,             # Years since creation
  "last_accessed": "2026-01-20T10:30:00",
  "consolidated_from": []     # Merged point IDs
}
```

### 5. Drift Detection (`src/drift.py`)

**Purpose**: Policy evolution analysis

**Algorithm**:
1. Group embeddings by year
2. Compute centroid for each year
3. Calculate cosine similarity between consecutive years
4. Convert to drift score (1 - similarity)
5. Classify severity

**Output**:
```json
{
  "from_year": "2020",
  "to_year": "2021",
  "drift_score": 0.45,
  "severity": "HIGH",
  "samples_year1": 23,
  "samples_year2": 31,
  "similarity": 0.55
}
```

### 6. Recommendations (`src/recommendations.py`)

**Purpose**: Cross-policy similarity analysis

**Algorithm**:
1. Sample random embedding from source policy
2. Search for similar vectors in other policies
3. Keep best match per policy
4. Return ranked recommendations

**Uses**:
- Policy comparison
- Impact assessment
- Strategy alignment analysis

### 7. REST API (`src/api.py`)

**Architecture**: FastAPI with async handlers

**Features**:
- Request validation (Pydantic models)
- Rate limiting (slowapi)
- Structured error handling
- Comprehensive logging
- Type hints throughout

**Rate Limits**:
- Default: 200/minute
- Query: 20/minute
- Drift: 10/minute
- Ingest: 5/minute

## Data Schema

### Point Payload (policy_data collection)

```python
{
  # Required
  "policy_id": "NREGA",           # Policy name
  "content": "...",               # Full text
  "year": 2023,                   # Year
  "modality": "temporal",         # budget/news/temporal
  
  # Memory tracking
  "decay_weight": 1.0,            # Relevance (0-1.5)
  "access_count": 0,              # Times accessed
  "age_years": 1,                 # Age in years
  "last_accessed": "ISO-8601",    # Last access time
  "last_decay_update": "ISO-8601",# Last decay update
  
  # Modality-specific
  "sentiment": "positive",        # News/temporal sentiment
  "allocation_crores": 1000.0,    # Budget-specific
  "expenditure_crores": 950.0,    # Budget-specific
  "headline": "...",              # News-specific
  
  # Consolidation
  "consolidated_from": []         # Merged point IDs
}
```

## Performance Considerations

### Embedding Efficiency
- **Model**: all-MiniLM-L6-v2 (lightweight, 22M params)
- **Speed**: ~1000 texts/sec on CPU
- **Accuracy**: Competitive on semantic similarity benchmarks

### Vector Search
- **Index Type**: HNSW (Hierarchical Navigable Small World)
- **Search Time**: <100ms for 10K vectors
- **Scalability**: Qdrant handles 1M+ vectors efficiently

### Memory Management
- **Decay Computation**: O(n) where n = collection size
- **Consolidation**: O(n²) but limited to year/policy
- **Batch Operations**: Reduce API calls via upsert batching

## Deployment Scenarios

### Development
```
Local Machine
├─ Qdrant (docker)
├─ FastAPI (uvicorn)
└─ CLI tools
```

### Production
```
Server Cluster
├─ Qdrant Cluster (persistent storage)
├─ Multiple API replicas (load balanced)
├─ Separate embedding worker (GPU)
└─ Monitoring & logging (ELK stack)
```

## Extensibility

### Adding New Policies
1. Add data files to `Data/` directory
2. Update `POLICY_MAPPINGS` in `cli.py`
3. Run `python cli.py ingest-all`

### Adding New Modalities
1. Create ingestion logic in `cli.py`
2. Set `modality` field in payload
3. Update intent detection in `reasoning.py`

### Custom Embedding Models
1. Update `EMBEDDING_MODEL` in `config.py`
2. Note new vector dimension in `VECTOR_DIMENSION`
3. Recreate collection (breaking change)

---

For implementation details, see docstrings in source files. For usage, see [EXAMPLES.md](EXAMPLES.md).
