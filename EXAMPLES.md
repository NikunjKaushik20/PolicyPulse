# Usage Examples

Complete examples for using PolicyPulse API and CLI tools.

## Prerequisites

Ensure you have completed [SETUP.md](SETUP.md):
- ✅ Python dependencies installed
- ✅ Qdrant running (`docker ps | grep qdrant`)
- ✅ Data ingested (`python cli.py ingest-all`)
- ✅ API server running (`uvicorn src.api:app`)

## Quick Start Examples

### 1. Health Check

**Check API is running:**
```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "service": "PolicyPulse API",
  "version": "1.0",
  "status": "operational"
}
```

**Check database connectivity:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "qdrant": "connected",
  "api": "operational",
  "collections": 2
}
```

## Query Examples

### Example 1: Simple Policy Query

**Question**: What is NREGA about?

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "NREGA",
    "question": "What is NREGA about?"
  }'
```

**Full Response:**
```json
{
  "query": "What is NREGA about?",
  "policy_id": "NREGA",
  "steps": [
    {
      "step": 1,
      "action": "Embedded query",
      "details": "384-dimensional vector"
    },
    {
      "step": 2,
      "action": "No year detected",
      "details": "Searching all years"
    },
    {
      "step": 3,
      "action": "No specific intent detected",
      "details": "Searching all modalities"
    },
    {
      "step": 4,
      "action": "Retrieved 5 results",
      "top_score": 0.856
    },
    {
      "step": 5,
      "action": "Reinforced 5 accessed memories"
    },
    {
      "step": 6,
      "action": "Answer synthesized",
      "confidence": 0.782
    }
  ],
  "retrieved_points": [
    {
      "rank": 1,
      "score": 0.856,
      "year": "2005",
      "modality": "temporal",
      "content_preview": "NREGA (Mahatma Gandhi National Rural Employment Guarantee Act) is a social security and public works scheme...",
      "decay_weight": 0.92,
      "access_count": 3
    }
  ],
  "final_answer": "NREGA is the Mahatma Gandhi National Rural Employment Guarantee Act..."
}
```

### Example 2: Budget Query with Year Filter

**Question**: How much was allocated to PM-KISAN in 2020?

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "PM-KISAN",
    "question": "Budget allocation for PM-KISAN in 2020?",
    "top_k": 5
  }'
```

**Key Response Features**:
- **Step 2**: Detected year 2020 → filtered results to that year
- **Step 3**: Detected budget query keywords → filtered to budget modality
- **Retrieved Points**: All from budget modality, year 2020
- **Confidence**: 0.91 (high due to specific filters)

### Example 3: News/Discourse Query

**Question**: What was the media coverage of Swachh Bharat in 2017?

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "SWACHH-BHARAT",
    "question": "News and media coverage of Swachh Bharat in 2017"
  }'
```

**Key Response Features**:
- **Step 3**: Detected keywords "news" and "media" → filtered to news modality
- **Retrieved Points**: News articles and headlines from 2017
- **Sentiment**: Each news item includes sentiment classification

### Example 4: Policy Intent Query

**Question**: What were the original objectives of Digital India?

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "DIGITAL-INDIA",
    "question": "What is the original purpose and intent of Digital India?"
  }'
```

**Key Response Features**:
- **Step 3**: Detected keywords "purpose", "intent" → filtered to temporal modality
- **Retrieved Points**: Policy evolution documents
- **Answer**: Multi-section synthesis of temporal documents

## Drift Analysis Examples

### Example 1: Detect Policy Evolution

**Question**: How has NREGA's focus changed from 2010 to 2023?

```bash
curl -X POST http://localhost:8000/drift \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "NREGA",
    "modality": "temporal"
  }'
```

**Response:**
```json
{
  "policy_id": "NREGA",
  "timeline": [
    {
      "from_year": "2005",
      "to_year": "2010",
      "drift_score": 0.24,
      "severity": "MEDIUM",
      "samples_year1": 45,
      "samples_year2": 52,
      "similarity": 0.76
    },
    {
      "from_year": "2010",
      "to_year": "2015",
      "drift_score": 0.38,
      "severity": "HIGH",
      "samples_year1": 52,
      "samples_year2": 61,
      "similarity": 0.62
    },
    {
      "from_year": "2015",
      "to_year": "2020",
      "drift_score": 0.19,
      "severity": "LOW",
      "samples_year1": 61,
      "samples_year2": 58,
      "similarity": 0.81
    }
  ],
  "max_drift": {
    "from_year": "2010",
    "to_year": "2015",
    "drift_score": 0.38,
    "severity": "HIGH",
    "samples_year1": 52,
    "samples_year2": 61,
    "similarity": 0.62
  },
  "total_periods": 3
}
```

**Interpretation**:
- Period 2010-2015 shows **HIGH drift** (0.38) → Major policy changes
- Similarity dropped from 0.76 to 0.62 → Significant semantic shift
- Possible reasons: Implementation changes, amended guidelines, updated priorities

### Example 2: Budget Drift Analysis

**Question**: How have budget allocations changed for Skill India?

```bash
curl -X POST http://localhost:8000/drift \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "SKILL-INDIA",
    "modality": "budget"
  }'
```

This shows financial allocation patterns rather than semantic drift.

### Example 3: News Sentiment Drift

**Question**: How has news sentiment around Digital India changed?

```bash
curl -X POST http://localhost:8000/drift \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "DIGITAL-INDIA",
    "modality": "news"
  }'
```

High drift in news data indicates:
- Changing public perception
- Different media narratives
- Shifting focus areas

## Recommendations Examples

### Example 1: Find Related Policies

**Question**: Which policies are similar to PM-KISAN?

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "PM-KISAN",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "policy_id": "PM-KISAN",
  "recommendations": [
    {
      "policy_id": "NREGA",
      "year": "2020",
      "similarity_score": 0.78,
      "sample_text": "NREGA provides guaranteed employment to rural workers, similar to income support mechanisms..."
    },
    {
      "policy_id": "AYUSHMAN-BHARAT",
      "year": "2019",
      "similarity_score": 0.72,
      "sample_text": "Healthcare and livelihood support schemes complement income protection programs..."
    },
    {
      "policy_id": "SKILL-INDIA",
      "year": "2021",
      "similarity_score": 0.68,
      "sample_text": "Skill development enables farmers to diversify income sources..."
    }
  ],
  "count": 3
}
```

### Example 2: Find Related Policy in Specific Year

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "SWACHH-BHARAT",
    "year": 2019,
    "top_k": 3
  }'
```

Restricts recommendations to policies with data from 2019.

## Memory Management Examples

### Example 1: Check Memory Health

**Question**: How is the memory system performing?

```bash
curl http://localhost:8000/memory/health
```

**Response:**
```json
{
  "total_points": 15234,
  "total_accesses": 3456,
  "avg_access_per_point": 0.23,
  "avg_decay_weight": 0.87,
  "min_decay_weight": 0.45,
  "max_decay_weight": 1.5,
  "age_distribution": {
    0: 2100,
    1: 3200,
    2: 4500,
    3: 2800,
    4: 1200,
    5: 434
  }
}
```

**Interpretation**:
- **avg_decay_weight**: 0.87 → Most data is reasonably relevant
- **age_distribution**: Shows spread across years (good coverage)
- If avg_decay_weight drops below 0.7, apply decay

### Example 2: Apply Time Decay

**Question**: Reduce relevance of older data?

```bash
curl -X POST "http://localhost:8000/memory/decay?policy_id=NREGA"
```

**Response:**
```json
{
  "policy_id": "NREGA",
  "points_updated": 1567
}
```

Applies exponential decay: `weight = exp(-0.1 * age_years)`

### Example 3: Consolidate Memories

**Question**: Merge duplicate NREGA documents from 2020?

```bash
curl -X POST "http://localhost:8000/memory/consolidate?policy_id=NREGA&year=2020&threshold=0.95"
```

**Response:**
```json
{
  "policy_id": "NREGA",
  "year": "2020",
  "memories_consolidated": 12,
  "threshold": 0.95
}
```

Merges 12 highly similar documents (cosine similarity ≥ 0.95).

### Example 4: Check Specific Policy Health

```bash
curl "http://localhost:8000/memory/health?policy_id=DIGITAL-INDIA"
```

Returns memory metrics for just DIGITAL-INDIA.

## Document Ingestion Examples

### Example 1: Ingest Custom Policy Document

**Question**: Add a new policy document to the system?

```bash
curl -X POST http://localhost:8000/ingest-document \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "NREGA",
    "year": "2023",
    "modality": "temporal",
    "content": "This is a detailed document about NREGA implementation in 2023. The policy focuses on rural employment guarantee with emphasis on infrastructure development and skill enhancement. Key objectives include: 1) Providing 100 days of guaranteed employment per household per financial year. 2) Generating durable assets. 3) Strengthening natural resource base. Implementation includes wage payment at prevailing minimum wage rate, with preference for women and SC/ST workers.",
    "filename": "nrega_2023_implementation.txt"
  }'
```

**Response:**
```json
{
  "status": "success",
  "policy_id": "NREGA",
  "chunks_added": 2,
  "year": "2023",
  "modality": "temporal",
  "chunks_preview": [
    "This is a detailed document about NREGA implementation...",
    "Implementation includes wage payment at prevailing minimum..."
  ]
}
```

### Example 2: Ingest Budget Data

```bash
curl -X POST http://localhost:8000/ingest-document \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "SWACHH-BHARAT",
    "year": "2023",
    "modality": "budget",
    "content": "Swachh Bharat Mission 2023 Budget Allocation: Total: Rs 15,000 crore Focus Areas: 1) Toilet construction - Rs 6,000 crore 2) Waste management - Rs 5,000 crore 3) Awareness programs - Rs 2,500 crore 4) Infrastructure - Rs 1,500 crore Expected outcomes: 500,000 new toilets, 10,000 waste processing units",
    "filename": "sbm_2023_budget.csv"
  }'
```

## CLI Examples

### Example 1: Reset Database

```bash
python cli.py reset-db
```

⚠️ **Warning**: Deletes all ingested data

**Output:**
```
🔄 Resetting database...
🗑️  Deleted old collection
✅ Created fresh collection!
```

### Example 2: Ingest All Data

```bash
python cli.py ingest-all
```

**Output:**
```
📦 Ingesting policy data...
✅ NREGA budgets: 234 chunks ingested
✅ NREGA news: 156 chunks ingested
✅ NREGA temporal: 89 chunks ingested
...
🎉 Ingestion complete! Total ingested: 15,234 chunks across 10 policies
```

## Advanced Examples

### Example 1: Compare Two Policies

```bash
# Get recommendations for Policy A
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"policy_id": "PM-KISAN", "top_k": 10}' \
  | python -m json.tool

# Get recommendations for Policy B
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"policy_id": "NREGA", "top_k": 10}' \
  | python -m json.tool
```

Compare similarity scores to understand policy relationships.

### Example 2: Track Policy Evolution Over Decade

```bash
# Get drift data
curl -X POST http://localhost:8000/drift \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "DIGITAL-INDIA",
    "modality": "temporal",
    "start_year": 2015,
    "end_year": 2025
  }' | python -m json.tool | grep -A 5 "severity"
```

Shows drift severity for each period - identify major inflection points.

### Example 3: Monitor System Health

```bash
# Check API health
curl http://localhost:8000/health

# Check collection stats
curl http://localhost:8000/stats

# Check memory health
curl http://localhost:8000/memory/health

# Monitor all three periodically
watch -n 10 'curl -s http://localhost:8000/health | python -m json.tool'
```

## Python Client Examples

### Basic Query
```python
import requests
import json

api_url = "http://localhost:8000"

# Query endpoint
response = requests.post(
    f"{api_url}/query",
    json={
        "policy_id": "NREGA",
        "question": "What are the key objectives?",
        "top_k": 5
    }
)

result = response.json()
print(f"Confidence: {result['final_answer']}")
```

### Drift Analysis
```python
import requests

response = requests.post(
    "http://localhost:8000/drift",
    json={
        "policy_id": "NREGA",
        "modality": "temporal"
    }
)

timeline = response.json()["timeline"]
for period in timeline:
    if period["severity"] in ["HIGH", "CRITICAL"]:
        print(f"Major change: {period['from_year']} → {period['to_year']}")
```

## Performance Tips

1. **Use filters** (year, modality) to reduce search space
2. **Batch operations**: Use consolidate endpoint during off-peak hours
3. **Monitor decay**: Apply time decay when avg_decay_weight < 0.7
4. **Cache results**: Store frequently queried results locally
5. **Use top_k=5 or less** for faster responses

## Troubleshooting Examples

### Query Returns No Results
```bash
# Check memory health first
curl http://localhost:8000/memory/health

# Try different policy_id
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": "RTI",
    "question": "What is RTI?",
    "top_k": 10
  }'
```

### API is Slow
```bash
# Check if consolidation needed
curl http://localhost:8000/memory/health | grep avg_decay_weight

# If low, consolidate
curl -X POST "http://localhost:8000/memory/consolidate?policy_id=NREGA&year=2020"
```

### Qdrant Connection Issues
```bash
# Check Qdrant health
docker logs policypulse-qdrant

# Check if port 6333 is accessible
curl http://localhost:6333/health
```

---

**Next Steps**:
- 📖 Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand system design
- 🔧 See [SETUP.md](SETUP.md) for deployment options
- 🎯 Start building your analysis queries!
