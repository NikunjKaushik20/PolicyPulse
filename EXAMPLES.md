# Examples

Real inputs and outputs from PolicyPulse. These are actual test cases we ran during development, not hypothetical scenarios. We included failures to show realistic behavior.

---

## Example 1: Basic Policy Query

**Input:**
```json
POST /query
{
  "query_text": "What is the wage rate under NREGA?",
  "top_k": 3
}
```

**Output:**
```json
{
  "query": "What is the wage rate under NREGA?",
  "final_answer": "NREGA (2024): Budget allocation was Rs 86,000 crore with average wage rates of Rs 255 per day, though inflation eroded real value over time.\n\nNREGA (2023): Allocated Rs 60,000 crore. Focus: Clearing wage arrears",
  "retrieved_points": [
    {
      "rank": 1,
      "policy_id": "NREGA",
      "year": "2024",
      "modality": "temporal",
      "score": 0.7113,
      "content_preview": "Budget allocation reached Rs 86,000 crore with wage rates increased to Rs 255 per day on average..."
    },
    {
      "rank": 2,
      "policy_id": "NREGA",
      "year": "2023",
      "modality": "budget",
      "score": 0.6891
    }
  ],
  "confidence_score": 0.700,
  "confidence_label": "High"
}
```

**What happened:**
- Detected policy: NREGA (keyword match)
- Vector search found 2024 temporal data as best match (score 0.71)
- Time-decay favored recent years (2024 weight 0.98)
- Answer shows exact year and source modality for auditability

---

## Example 2: Year-Specific Budget Query

**Input:**
```json
POST /query
{
  "query_text": "How much was allocated to PM-KISAN in 2021?",
  "top_k": 3
}
```

**Output:**
```json
{
  "final_answer": "Budget (2021): PM-KISAN budget 2021: Allocated Rs 65,000 crore. Focus: Expanding beneficiary coverage",
  "retrieved_points": [
    {
      "rank": 1,
      "year": "2021",
      "modality": "budget",
      "score": 0.8412
    }
  ],
  "confidence_score": 0.841,
  "confidence_label": "High"
}
```

**Why high confidence:** Direct year match + budget keyword in query. This is the factual lookup the system handles best.

---

## Example 3: Multilingual Query (Hindi)

**Input:**
```json
POST /query
{
  "query_text": "मुझे NREGA के बारे में बताओ",
  "language": "hi"
}
```

**Processing:**
1. Detected Hindi via `langdetect`
2. Translated to English: "Tell me about NREGA"
3. Ran vector search
4. Translated answer back to Hindi

**Output:**
```json
{
  "detected_language": "hi",
  "final_answer": "NREGA (महात्मा गांधी राष्ट्रीय ग्रामीण रोजगार गारंटी अधिनियम) एक सामाजिक कल्याण कानून है जो ग्रामीण परिवारों को 100 दिन का रोजगार गारंटी प्रदान करता है...",
  "confidence_label": "High"
}
```

---

## Example 4: Policy Drift Analysis

**Input:**
```json
POST /drift
{
  "policy_id": "NREGA",
  "modality": "temporal"
}
```

**Output:**
```json
{
  "policy_id": "NREGA",
  "modality": "temporal",
  "total_periods": 19,
  "max_drift": {
    "from_year": "2019",
    "to_year": "2020",
    "drift_score": 0.742,
    "severity": "CRITICAL"
  },
  "timeline": [
    {"from_year": "2005", "to_year": "2006", "drift_score": 0.312, "severity": "MEDIUM"},
    {"from_year": "2019", "to_year": "2020", "drift_score": 0.742, "severity": "CRITICAL"},
    {"from_year": "2020", "to_year": "2021", "drift_score": 0.421, "severity": "HIGH"}
  ]
}
```

**Validation:** We manually checked the 2019→2020 CRITICAL drift. Reality: COVID pandemic, NREGA budget went from Rs 60,000 crore to Rs 1.11 lakh crore. **System correctly flagged this.**

---

## Example 5: Eligibility Check - Rural Farmer

**Input:**
```json
POST /eligibility/check
{
  "age": 45,
  "income": 50000,
  "occupation": "farmer",
  "location_type": "rural",
  "land_ownership": true,
  "has_toilet": true,
  "willingness_manual_work": true
}
```

**Output:**
```json
[
  {
    "policy_id": "PM-KISAN",
    "policy_name": "Pradhan Mantri Kisan Samman Nidhi",
    "description": "₹6000 annual income support for farmers",
    "benefits": "₹6000 per year in 3 installments",
    "documents_required": ["Land ownership documents", "Aadhaar card", "Bank account"],
    "application_link": "https://pmkisan.gov.in/",
    "priority": "HIGH"
  },
  {
    "policy_id": "NREGA",
    "policy_name": "National Rural Employment Guarantee Act",
    "description": "100 days guaranteed wage employment",
    "benefits": "₹209-318 per day, 100 days/year",
    "priority": "HIGH"
  },
  {
    "policy_id": "SKILL-INDIA",
    "policy_name": "Skill India Mission",
    "description": "Vocational training programs",
    "priority": "MEDIUM"
  }
]
```

**Why these 3:**
- PM-KISAN: farmer + land ownership + income < ₹2L → eligible
- NREGA: rural + willingness for manual work → eligible
- Skill India: age 45 within 15-50 range → eligible
- Swachh Bharat: NOT shown (user already has toilet)

---

## Example 6: Eligibility Check - Urban Professional

**Input:**
```json
POST /eligibility/check
{
  "age": 30,
  "income": 800000,
  "occupation": "software engineer",
  "location_type": "urban",
  "land_ownership": false
}
```

**Output:**
```json
[
  {
    "policy_id": "RTI",
    "policy_name": "Right to Information",
    "description": "Access to government information",
    "priority": "MEDIUM"
  },
  {
    "policy_id": "DIGITAL-INDIA",
    "policy_name": "Digital India Initiative",
    "description": "Digital literacy and services",
    "priority": "MEDIUM"
  }
]
```

**Why only 2:** High income (₹8L) disqualifies from most welfare schemes. RTI and Digital India have no income restrictions.

---

## Example 7: Document OCR - Aadhaar Card

**Scenario:** User uploads photo of printed Aadhaar card.

**OCR Extraction:**
```
GOVERNMENT OF INDIA
UNIQUE IDENTIFICATION AUTHORITY OF INDIA
Name: Ramesh Kumar
DOB: 15/03/1985
Address: Village Kamalpura, District Alwar, Rajasthan - 301001
```

**UI Response:**
```
✅ OCR Extraction Complete

Extracted Fields:
  Name: Ramesh Kumar
  DOB: 15/03/1985
  Location: Rajasthan

Auto-Detection:
  Document Type: Aadhaar Card
  Confidence: 94%

Age calculated: 40 years
Location type: Rural (detected from village address)
```

User can override if detection is wrong, then proceed to eligibility check.

---

## Example 8: Audio Transcription (Hindi)

**Scenario:** User uploads MP3: "किसान योजनाओं के बारे में बताइए"

**Processing:**
1. Google Speech Recognition transcribes to Hindi text
2. Translated: "Tell me about farmer schemes"
3. Policy detection: keyword "farmer" → PM-KISAN
4. Standard query pipeline

**Output:**
```
🎧 Transcription: किसान योजनाओं के बारे में बताइए
🔍 Detected Policy: PM-KISAN

Answer: PM-KISAN provides ₹6,000 annual income support to farmers...
```

**Accuracy:** 90% on clear audio, 60% with background noise.

---

## Example 9: Edge Case - Ambiguous Query

**Input:**
```json
POST /query
{
  "query_text": "government schemes",
  "top_k": 3
}
```

**Output:**
```json
{
  "final_answer": "NREGA (2024): Budget allocation reached Rs 86,000 crore...",
  "retrieved_points": [
    {"policy_id": "NREGA", "score": 0.421},
    {"policy_id": "NREGA", "score": 0.398}
  ],
  "confidence_score": 0.402,
  "confidence_label": "Low"
}
```

**Behavior:** Generic query → low similarity scores → low confidence. System correctly signals uncertainty. Defaults to NREGA (most common policy).

---

## Example 10: Edge Case - Out-of-Scope Query

**Input:**
```json
POST /query
{
  "query_text": "cryptocurrency regulations in India",
  "top_k": 5
}
```

**Output:**
```json
{
  "final_answer": "No relevant information found. Please try a different query or select a specific policy.",
  "retrieved_points": [],
  "confidence_score": 0.0,
  "confidence_label": "Low"
}
```

**Behavior:** System doesn't hallucinate. Returns empty rather than inventing an answer.

---

## Example 11: Historical Query

**Input:**
```json
POST /query
{
  "query_text": "When was NREGA first introduced?",
  "top_k": 3
}
```

**Output:**
```json
{
  "final_answer": "NREGA (2005): The National Rural Employment Guarantee Act (NREGA) was passed by Parliament, marking a historic moment in India's social welfare legislation...",
  "retrieved_points": [
    {
      "year": "2005",
      "modality": "temporal",
      "score": 0.8123,
      "decay_weight": 0.135
    }
  ],
  "confidence_score": 0.812
}
```

**Key observation:** Despite low decay weight (0.135 for 21-year-old data), the system found the right answer because semantic similarity (0.81) was very high. Time decay is a multiplier, not a filter.

---

## Example 12: Policy Recommendations

**Input:**
```json
POST /recommendations
{
  "policy_id": "NREGA",
  "top_k": 3
}
```

**Output:**
```json
{
  "policy_id": "NREGA",
  "recommendations": [
    {
      "policy_id": "PM-KISAN",
      "similarity_score": 0.734,
      "sample_text": "Pradhan Mantri Kisan Samman Nidhi provides direct income support to farmers..."
    },
    {
      "policy_id": "SKILL-INDIA",
      "similarity_score": 0.612,
      "sample_text": "Skill India Mission provides vocational training for rural youth..."
    },
    {
      "policy_id": "SWACHH-BHARAT",
      "similarity_score": 0.589,
      "sample_text": "Swachh Bharat Mission focuses on rural sanitation infrastructure..."
    }
  ]
}
```

**Interpretation:** Rural employment scheme is semantically similar to farmer income support and other rural development programs.

---

## Example 13: Failed OCR (Handwritten Document)

**Scenario:** User uploads handwritten income certificate.

**OCR Output:**
```
j@#$ kl23 asdf... (gibberish)
```

**System Response:**
```
⚠️ OCR Extraction Quality Warning

The extracted text contains significant errors. Common causes:
- Handwritten documents (OCR works best on printed text)
- Low-quality scans
- Non-English text without language pack

Extracted: j@#$ kl23 asdf...

Suggestion: Try uploading a clearer printed document or type the content manually.
```

**Honest behavior:** We don't pretend it worked. We show what we got and suggest alternatives.

---

## Example 14: Translation Timeout

**Scenario:** Network is slow, Google Translate API takes >5 seconds.

**System behavior:**
1. Attempt translation
2. Hit 5-second timeout
3. Fallback to original English text

**Log:**
```
WARNING: Translation timeout for query in Hindi
Falling back to English response
```

**User sees:** English answer instead of Hindi, but query completes. Core search works offline; translation is graceful degradation.

---

## Example 15: Rate Limit Hit

**Response:**
```json
HTTP 429 Too Many Requests
{
  "detail": "Rate limit exceeded: 20 requests per minute for this endpoint"
}
```

---

## Example 16: Invalid Input

**Input:**
```json
POST /query
{
  "query_text": "x",
  "top_k": 3
}
```

**Response:**
```json
HTTP 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "query_text"],
      "msg": "Query too short (minimum 3 characters)",
      "type": "value_error"
    }
  ]
}
```

---

## Observed Query Patterns

From 200+ test queries during development:

| Pattern | Example | Success Rate |
|---------|---------|--------------|
| Definition | "What is RTI?" | 95% |
| Budget lookup | "NREGA budget 2020" | 100% |
| Eligibility | "Can I get PM-KISAN?" | 85% |
| Evolution | "How has NEP changed?" | 70% |
| Comparison | "NREGA vs PM-KISAN" | 60% |

**Weakest area:** Cross-policy comparisons. System is designed for single-policy queries.

---

## Performance Benchmarks

Measured on Intel i5, 8GB RAM, SSD:

| Operation | Average | 95th Percentile |
|-----------|---------|-----------------|
| Simple query (text) | 180ms | 250ms |
| Query (first run, model loading) | 450ms | 600ms |
| Drift analysis | 850ms | 1200ms |
| With translation | 480ms | 650ms |
| With TTS | 680ms | 900ms |
| Image OCR + query | 2.1s | 3.5s |

---

## Streamlit UI Walkthrough

### Chat Tab
1. User types: "What was NREGA budget in 2010?"
2. System auto-detects policy: NREGA
3. Shows answer with evidence cards
4. Click "📊 Evidence" expander to see source year, modality, similarity score

### Drift Tab
1. Select policy: NREGA
2. Select modality: temporal
3. Click "🔍 Analyze"
4. View max drift period (2019→2020, score 0.74), timeline with color-coded severity

### Upload Tab
1. Upload MP3 file (voice query)
2. System transcribes
3. Auto-detects policy
4. User can override
5. Click "⚡ INGEST" to add to database

### Recommendations Tab
1. Select policy: NREGA
2. Set count: 5
3. Click "🔍 Get Recommendations"
4. View related policies sorted by similarity

---

## Test Dataset Details

Evaluation uses 20 queries across 2 policies:

**NREGA (10 queries):**
- 3 budget queries (e.g., "What was budget in 2020?")
- 4 evolution queries (e.g., "How did it change in 2009?")
- 2 discourse queries (e.g., "What was public opinion in 2023?")
- 1 intent query ("What was original intent in 2005?")

**RTI (10 queries):**
- Similar distribution

**Ground truth:** Manually created based on verified policy facts. Not independently validated by domain experts.

**Results:**
- Year accuracy: 100% (for year-specific queries)
- Modality accuracy: 60% (budget vs temporal often confused)
- Average top-1 similarity: 0.575

**What 60% modality accuracy means:** If you ask "What happened to NREGA in 2014?", you'll get 2014 data (correct year), but might get budget allocation when you wanted policy evolution text. Answer is still useful, just not the exact type expected.

---

These examples are from actual system runs. No cherry-picking. We included failures (OCR gibberish, low-confidence queries) to show realistic behavior.
