# Examples

This document shows real inputs, outputs, and edge cases for PolicyPulse.

---

## Example 1: Basic Policy Query

**Input**:
```json
POST /query
{
  "query_text": "What is the wage rate under NREGA?",
  "top_k": 3
}
```

**Output**:
```json
{
  "query": "What is the wage rate under NREGA?",
  "final_answer": "NREGA (2025): Budget allocation reached Rs 90,000 crore with wage rates increased to Rs 255 per day on average, though inflation eroded real value over time.\n\nBudget (2024): NREGA budget 2024: Allocated Rs 86000 crore. Focus: Clearing wage arrears",
  "retrieved_points": [
    {
      "rank": 1,
      "policy_id": "NREGA",
      "year": "2025",
      "modality": "temporal",
      "score": 0.7823,
      "content_preview": "Budget allocation reached Rs 90,000 crore with introduction of AI-based attendance and monitoring systems. Wage rates increased to Rs 255 per day on average..."
    },
    {
      "rank": 2,
      "policy_id": "NREGA",
      "year": "2024",
      "modality": "budget",
      "score": 0.6891,
      "content_preview": "NREGA budget 2024: Allocated Rs 86000 crore, spent Rs 82000 crore. Focus: Clearing wage arrears"
    }
  ],
  "confidence_score": 0.736,
  "confidence_label": "High"
}
```

**Interpretation**: The system correctly identifies this as an NREGA query, retrieves recent wage information (2024-2025), and synthesizes an answer from both temporal evolution data and budget records.

---

## Example 2: Budget-Specific Query

**Input**:
```json
POST /query
{
  "query_text": "How much was allocated to PM-KISAN in 2021?",
  "top_k": 5
}
```

**Output**:
```json
{
  "final_answer": "Budget (2021): PM-KISAN budget 2021: Allocated Rs 65000 crore. Focus: Expanding beneficiary coverage",
  "retrieved_points": [
    {
      "rank": 1,
      "policy_id": "PM-KISAN",
      "year": "2021",
      "modality": "budget",
      "score": 0.8412,
      "content_preview": "PM-KISAN budget 2021: Allocated Rs 65000 crore, spent Rs 58000 crore. Focus: Expanding beneficiary coverage"
    }
  ],
  "confidence_score": 0.841,
  "confidence_label": "High"
}
```

**Interpretation**: Year-specific query retrieves exact budget data. High confidence because the query directly matches stored data.

---

## Example 3: Policy Evolution Query

**Input**:
```json
POST /query
{
  "query_text": "How has RTI changed since 2005?",
  "top_k": 5
}
```

**Output**:
```json
{
  "final_answer": "RTI (2005): The Right to Information Act was passed by Parliament, replacing the Freedom of Information Act, 2002. The Act established a framework for citizens to access government information...\n\nRTI (2019): The RTI Amendment Act 2019 sparked controversy by changing the tenure and salary conditions of Information Commissioners...",
  "retrieved_points": [
    {
      "rank": 1,
      "policy_id": "RTI",
      "year": "2005",
      "modality": "temporal",
      "score": 0.7234
    },
    {
      "rank": 2,
      "policy_id": "RTI",
      "year": "2019",
      "modality": "temporal",
      "score": 0.6891
    },
    {
      "rank": 3,
      "policy_id": "RTI",
      "year": "2010",
      "modality": "temporal",
      "score": 0.6542
    }
  ],
  "confidence_score": 0.689
}
```

**Interpretation**: Evolution queries retrieve multiple years. The system shows origin (2005), significant change (2019 amendment), and intermediate years for context.

---

## Example 4: Drift Analysis

**Input**:
```
GET /drift/NREGA
```

**Output**:
```json
{
  "policy_id": "NREGA",
  "total_periods": 19,
  "max_drift": {
    "from_year": "2019",
    "to_year": "2020",
    "drift_score": 0.742,
    "severity": "CRITICAL",
    "samples_year1": 8,
    "samples_year2": 12
  },
  "timeline": [
    {
      "from_year": "2005",
      "to_year": "2006",
      "drift_score": 0.312,
      "severity": "MEDIUM"
    },
    {
      "from_year": "2019",
      "to_year": "2020",
      "drift_score": 0.742,
      "severity": "CRITICAL"
    }
  ]
}
```

**Interpretation**: 2019→2020 shows CRITICAL drift (0.742) corresponding to COVID emergency expansion. This is a real policy change: budget doubled from Rs 60,000 crore to Rs 1.11 lakh crore.

---

## Example 5: Eligibility Check

**Input**:
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

**Output**:
```json
[
  {
    "policy_id": "PM-KISAN",
    "policy_name": "Pradhan Mantri Kisan Samman Nidhi",
    "description": "₹6000 annual income support for farmers",
    "benefits": "₹6000 per year in 3 installments of ₹2000 each",
    "documents_required": ["Land ownership documents", "Aadhar card", "Bank account details"],
    "application_link": "https://pmkisan.gov.in/",
    "priority": "HIGH"
  },
  {
    "policy_id": "NREGA",
    "policy_name": "Mahatma Gandhi National Rural Employment Guarantee Act",
    "description": "100 days of guaranteed wage employment",
    "benefits": "₹209-318 per day wage, 100 days guaranteed employment per year",
    "documents_required": ["Job card", "Aadhar card", "Bank account details", "Address proof"],
    "application_link": "https://nrega.nic.in/",
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

**Interpretation**: Rural farmer with land ownership qualifies for PM-KISAN and NREGA. Age 45 is within Skill India's 15-45 range. Swachh Bharat not shown because user already has toilet.

---

## Example 6: Eligibility - Urban Professional

**Input**:
```json
POST /eligibility/check
{
  "age": 30,
  "income": 800000,
  "occupation": "software engineer",
  "location_type": "urban",
  "land_ownership": false,
  "has_toilet": true,
  "willingness_manual_work": false
}
```

**Output**:
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

**Interpretation**: High-income urban professional doesn't qualify for most welfare schemes. RTI applies to all citizens. Digital India has no restrictions.

---

## Example 7: Translation

**Input**:
```json
POST /query
{
  "query_text": "What is NREGA?",
  "language": "hi"
}
```

**Output**:
```json
{
  "final_answer": "मनरेगा (NREGA) एक सामाजिक सुरक्षा कानून है जो ग्रामीण परिवारों को 100 दिन का रोजगार गारंटी प्रदान करता है...",
  "confidence_label": "High"
}
```

**Interpretation**: Same retrieval pipeline, answer translated to Hindi via deep-translator.

---

## Example 8: Multimodal - Image Upload

**Scenario**: User uploads photo of Aadhaar card

**Process**:
1. Image uploaded via Streamlit UI
2. pytesseract extracts text: "UNIQUE IDENTIFICATION AUTHORITY OF INDIA... Name: Ramesh Kumar... DOB: 15/03/1985..."
3. System detects policy context from content (or uses default)
4. Query ingested into policy database if requested

**Output** (Streamlit UI):
```
✅ OCR Extraction Complete
Extracted Content Preview: UNIQUE IDENTIFICATION AUTHORITY OF INDIA...
Auto-Detection:
  Policy: DIGITAL-INDIA
  Year: 2024
```

---

## Example 9: Multimodal - Audio Query

**Scenario**: User speaks "Tell me about farmer schemes" in Hindi

**Process**:
1. Audio captured via microphone or uploaded file
2. SpeechRecognition transcribes to text
3. Text translated to English if needed
4. Standard query pipeline executes

**Transcription output**:
```
किसान योजनाओं के बारे में बताइए
→ Translated: Tell me about farmer schemes
→ Detected policy: PM-KISAN
```

---

## Example 10: Edge Case - Ambiguous Query

**Input**:
```json
POST /query
{
  "query_text": "government schemes"
}
```

**Output**:
```json
{
  "final_answer": "NREGA (2025): Budget allocation reached Rs 90,000 crore...",
  "retrieved_points": [
    {"policy_id": "NREGA", "score": 0.421},
    {"policy_id": "PM-KISAN", "score": 0.398},
    {"policy_id": "AYUSHMAN-BHARAT", "score": 0.387}
  ],
  "confidence_score": 0.402,
  "confidence_label": "Low"
}
```

**Interpretation**: Generic query gets low confidence. Results span multiple policies. System defaults to NREGA fallback but signals uncertainty.

---

## Example 11: Edge Case - No Relevant Data

**Input**:
```json
POST /query
{
  "query_text": "cryptocurrency regulations in India"
}
```

**Output**:
```json
{
  "final_answer": "No relevant information found. Please try rephrasing your question.",
  "retrieved_points": [],
  "confidence_score": 0.0,
  "confidence_label": "Low"
}
```

**Interpretation**: Query is outside policy coverage. System correctly returns empty rather than hallucinating.

---

## Example 12: Edge Case - Historical Query

**Input**:
```json
POST /query
{
  "query_text": "When was NREGA first introduced?"
}
```

**Output**:
```json
{
  "final_answer": "NREGA (2005): The National Rural Employment Guarantee Act (NREGA) was passed by Parliament, marking a historic moment in India's social welfare legislation. The Act guaranteed 100 days of wage employment per year to every rural household willing to do unskilled manual work. Initial rollout covered 200 districts across 27 states...",
  "retrieved_points": [
    {
      "policy_id": "NREGA",
      "year": "2005",
      "modality": "temporal",
      "score": 0.8123,
      "decay_weight": 0.135
    }
  ],
  "confidence_score": 0.812
}
```

**Interpretation**: Historical question correctly retrieves 2005 data despite time decay (weight 0.135). Historical queries work because semantic relevance overrides recency bias.

---

## Example 13: Recommendations

**Input**:
```
GET /recommendations/NREGA?count=3
```

**Output**:
```json
{
  "policy_id": "NREGA",
  "recommendations": [
    {
      "policy_id": "PM-KISAN",
      "similarity_score": 0.734,
      "sample_text": "Pradhan Mantri Kisan Samman Nidhi provides income support..."
    },
    {
      "policy_id": "SKILL-INDIA",
      "similarity_score": 0.612,
      "sample_text": "Skill India Mission provides vocational training..."
    },
    {
      "policy_id": "SWACHH-BHARAT",
      "similarity_score": 0.589,
      "sample_text": "Swachh Bharat Mission focuses on rural sanitation..."
    }
  ]
}
```

**Interpretation**: Rural employment scheme (NREGA) is most similar to farmer income support (PM-KISAN) and other rural development programs.

---

## API Error Handling

### Rate Limit Exceeded
```json
HTTP 429
{
  "detail": "Rate limit exceeded. 20/minute for this endpoint."
}
```

### Invalid Input
```json
HTTP 422
{
  "detail": [
    {
      "loc": ["body", "query_text"],
      "msg": "Query too short (min 3 characters)",
      "type": "value_error"
    }
  ]
}
```

### Server Error
```json
HTTP 500
{
  "detail": "ChromaDB query failed: connection error"
}
```

---

## Streamlit UI Walkthrough

### Chat Tab
1. Type question in chat input
2. System auto-detects policy from keywords
3. Answer displayed with evidence cards
4. Click "Evidence" expander to see source documents

### Drift Tab
1. Select policy from dropdown
2. Select modality (text/budget/news)
3. Click "Analyze"
4. View drift timeline with severity indicators

### Upload Tab
1. Upload file (TXT, PDF, image, audio, video)
2. Content extracted and previewed
3. Auto-detect policy and year
4. Override if needed
5. Click "INGEST" to add to database

### Recommendations Tab
1. Select policy to analyze
2. Optionally filter by year
3. Set number of recommendations
4. Click "Get Recommendations"
5. View related policies with similarity scores

### Advanced Tab
- Apply memory decay
- Export chat history
- View system stats and performance metrics

---

## Real Query Patterns (Observed During Testing)

| Pattern | Example | Detection |
|---------|---------|-----------|
| Definition | "What is RTI?" | `temporal` modality |
| Budget | "NREGA budget 2020" | `budget` modality |
| Eligibility | "Can I get PM-KISAN?" | Routes to `/eligibility/check` |
| Comparison | "NREGA vs PM-KISAN" | Returns both policies |
| Historical | "When did Digital India start?" | Retrieves origin year |
| Evolution | "How has NEP changed?" | Multi-year temporal |

---

## Performance Benchmarks

| Query Type | Avg Latency | 95th Percentile |
|------------|-------------|-----------------|
| Simple (1 policy) | 150ms | 220ms |
| Complex (multi-year) | 200ms | 350ms |
| Drift analysis | 800ms | 1200ms |
| With translation | +300ms | +500ms |
| With TTS | +500ms | +800ms |

Tested on: Intel i5, 16GB RAM, SSD
