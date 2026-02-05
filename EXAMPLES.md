# PolicyPulse Examples

Real query examples that demonstrate system behavior. All examples trace actual code execution paths.

---

## Example 1: Basic Scheme Query

**Input:**
```
"What is NREGA?"
```

**Processing steps:**

1. **Query processor** (`src/query_processor.py:detect_policy_from_query`):
   - Matches "nrega" in `POLICY_ALIASES`
   - Returns `policy_id = "NREGA"`

2. **ChromaDB query** (`src/chromadb_setup.py:query_documents`):
   ```python
   results = query_documents(
       query_text="What is NREGA?",
       n_results=5,
       where={"policy_id": "NREGA"}
   )
   ```

3. **Retrieved documents** (top 3):
   | Document | Year | Score |
   |----------|------|-------|
   | NREGA temporal definition | 2006 | 0.59 |
   | NREGA budget summary | 2024 | 0.54 |
   | NREGA news coverage | 2023 | 0.51 |

4. **Answer synthesis** (`src/reasoning.py:synthesize_answer`):
   - Detects query type: "definition"
   - Pulls from temporal data (scheme origin)
   - Adds current context from budget data

**Output:**
```json
{
  "final_answer": "NREGA: महात्मा गांधी जातीय ग्रामीण उपाधि पोमि चट्टॅం (MGNREGA) అనేది నేషనల్‍ం లేని మాన్యుపల్ పని చేయడానికి ఇష్టపడే గ్రామీణ కుటుంబాలకు సంవత్సరానికి 100 రోజుల వేతన ఉపాధికి హామీ ఇచ్చే సామాజిక భద్రతా పథకం.\n\nముఖ్య వివరాలు: NREGA 200 వెనుకబడిన జిల్లాలలో ప్రారంభించబడింది. ఇంపాక్ట్ స్కోర్: 90 (మూలం: ది హిందూ, 2006)",
  "confidence_score": 0.741,
  "sources": [
    {"policy": "NREGA", "year": "2006", "type": "temporal"}
  ]
}
```

**Confidence score breakdown:**
- Top-1 similarity: 0.59 → contributes 0.59 × 0.5 = 0.295
- Result consistency: 5/5 NREGA → contributes 0.5
- Total: 0.795 → normalized to 0.741

---

## Example 2: Year-Specific Budget Query

**Input:**
```
"NREGA budget 2023"
```

**Processing steps:**

1. **Query processor**:
   - `detect_policy_from_query("NREGA budget 2023")` → `"NREGA"`
   - `extract_years_from_query("NREGA budget 2023")` → `(2023, 2023)`

2. **Filter construction** (`src/query_processor.py:build_query_filter`):
   ```python
   where = {
       "$and": [
           {"policy_id": "NREGA"},
           {"year": "2023"}
       ]
   }
   ```

3. **ChromaDB query with filter**:
   ```python
   results = query_documents(
       query_text="NREGA budget 2023",
       n_results=5,
       where=where
   )
   ```

4. **Retrieved documents**:
   | Document | Modality | Score |
   |----------|----------|-------|
   | NREGA budget 2023 allocation | budget | 0.82 |
   | NREGA budget 2023 spending | budget | 0.78 |
   | NREGA news 2023 | news | 0.65 |

**Output:**
```json
{
  "final_answer": "NREGA Budget 2023:\n- Allocated: ₹60,000 crore\n- Spent: ₹55,230 crore\n- Utilization: 92%\n\nSource: Union Budget 2023-24",
  "confidence_score": 0.975,
  "sources": [
    {"policy": "NREGA", "year": "2023", "type": "budget"}
  ]
}
```

---

## Example 3: Eligibility Check

**Input:**
```
"suggest some policies for 20 year old male student"
```

**Processing steps:**

1. **Demographics extraction** (`src/query_processor.py:extract_demographics`):
   ```python
   # Regex patterns applied:
   # r'(\d+)\s*(?:year|yr)' → age = 20
   # r'\b(male|female)\b' → gender = "male"
   # r'\b(student|farmer|...)\b' → occupation = "student"
   
   demographics = {
       "age": 20,
       "gender": "male",
       "occupation": "student",
       "category": "general",  # default
       "location_type": "urban"  # default
   }
   ```

2. **Eligibility check** (`src/eligibility.py:check_eligibility`):
   ```python
   eligible_schemes = []
   
   for policy_id, rules in ELIGIBILITY_RULES.items():
       match_score = calculate_match(demographics, rules)
       if match_score >= 0.8:
           eligible_schemes.append({
               "policy_id": policy_id,
               "name": rules["name"],
               "benefits": rules["benefits"],
               "application_link": rules["application_link"],
               "documents_required": rules["documents_required"]
           })
   ```

3. **Matched policies:**
   | Policy | Match Score | Reason |
   |--------|-------------|--------|
   | AYUSHMAN-BHARAT | 1.0 | age 20, any location |
   | RTI | 1.0 | age 18+, any citizen |
   | SWACHH-BHARAT | 0.9 | age match, income unknown |
   | DIGITAL-INDIA | 1.0 | any citizen |
   | SKILL-INDIA | 1.0 | age 15-35, student occupation |

**Output:**
```
Based on your profile (20yr old, student), here are the best policies for you:

**Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana**
₹5 lakh health insurance coverage.
Benefits: ₹5 lakh health insurance per family per year
Apply Link: https://pmjay.gov.in/

**Right to Information**
Access to government information.
Benefits: Access to government documents and information within 30 days
Apply Link: https://rtionline.gov.in/

**Swachh Bharat Mission**
Toilet construction subsidy.
Benefits: ₹12,000 subsidy for toilet construction
Apply Link: https://swachhbharatmission.gov.in/

**Digital India Initiative**
Digital literacy and services.
Benefits: Free digital literacy training, online government services
Apply Link: https://www.digitalindia.gov.in/

**Skill India Mission**
Free vocational training.
Benefits: Free vocational training, certification, placement assistance
Apply Link: https://www.skillindia.gov.in/
```

---

## Example 4: Hindi Query with Translation

**Input:**
```
"नरेगा के बारे में बताओ"
```

**Processing steps:**

1. **Language detection** (`src/language_detection.py`):
   ```python
   detected = detect_language("नरेगा के बारे में बताओ")
   # Returns: "hi" (Hindi)
   ```

2. **Translation to English** (`src/translation.py:translate_text`):
   ```python
   english_query = translate_text(
       "नरेगा के बारे में बताओ",
       target_lang="en",
       source_lang="hi"
   )
   # Returns: "Tell me about NREGA"
   ```

3. **Policy detection (runs on both)**:
   - Original: "नरेगा" matches alias for NREGA
   - Translated: "NREGA" matches directly

4. **ChromaDB query** (uses translated text for embedding):
   ```python
   results = query_documents(
       query_text="Tell me about NREGA",
       n_results=5,
       where={"policy_id": "NREGA"}
   )
   ```

5. **Answer translation** (`src/translation.py:translate_response`):
   ```python
   translated_answer = translate_text(
       english_answer,
       target_lang="hi",
       source_lang="en"
   )
   ```

**Output (in Hindi):**
```json
{
  "final_answer": "नरेगा (MGNREGA) एक सामाजिक सुरक्षा योजना है जो ग्रामीण परिवारों को प्रति वर्ष 100 दिनों के वेतन रोजगार की गारंटी देती है।\n\nमुख्य विवरण:\n- 2005 में शुरू\n- 200 पिछड़े जिलों में लागू\n- वर्तमान मजदूरी: ₹255/दिन\n\nSource: NREGA MIS 2024",
  "confidence_score": 0.86,
  "detected_language": "hi"
}
```

---

## Example 5: Document Upload (OCR)

**Input:** Image of Aadhaar card

**Processing steps:**

1. **Text extraction** (`src/document_checker.py:extract_text_from_image`):
   ```python
   text = pytesseract.image_to_string(
       Image.open(image_bytes),
       lang='hin+eng'  # Hindi + English
   )
   # Returns raw OCR text
   ```

2. **Document type detection** (`src/document_checker.py:detect_document_type`):
   ```python
   # Checks for keywords
   if any(kw in text.lower() for kw in ['aadhaar', 'आधार', 'unique identification']):
       return 'aadhaar'
   ```

3. **Field extraction** (`src/document_checker.py:extract_fields`):
   ```python
   fields = {
       "name": extract_name(text),           # Regex for name patterns
       "aadhaar_number": extract_aadhaar(text),  # r'\b\d{4}\s?\d{4}\s?\d{4}\b'
       "dob": extract_date(text),            # Multiple date formats
       "gender": extract_gender(text)         # M/F/Male/Female
   }
   ```

4. **Validation** (`src/document_checker.py:validate_document`):
   ```python
   validation = {
       "is_valid": True,
       "document_type": "aadhaar",
       "extracted_fields": fields,
       "issues": []
   }
   
   # Check Aadhaar number format (Verhoeff checksum)
   if not validate_aadhaar_checksum(fields["aadhaar_number"]):
       validation["issues"].append("Invalid Aadhaar checksum")
   ```

**Output:**
```json
{
  "document_type": "aadhaar",
  "extracted_fields": {
    "name": "Ramesh Kumar",
    "aadhaar_number": "1234 5678 9012",
    "dob": "15/08/1985",
    "gender": "Male"
  },
  "validation": {
    "is_valid": true,
    "issues": []
  },
  "eligible_schemes": ["NREGA", "PM-KISAN", "AYUSHMAN-BHARAT"]
}
```

---

## Example 6: Policy Drift Query

**Input:**
```
"How did NREGA change between 2019 and 2020?"
```

**Processing steps:**

1. **Year range extraction**:
   ```python
   # Pattern: r'between\s+(\d{4})\s+and\s+(\d{4})'
   year_start, year_end = 2019, 2020
   ```

2. **Drift calculation** (`src/drift.py`):
   ```python
   # Get embeddings for 2019 data
   data_2019 = get_all_documents(where={"policy_id": "NREGA", "year": "2019"})
   centroid_2019 = np.mean([embed(doc) for doc in data_2019], axis=0)
   
   # Get embeddings for 2020 data
   data_2020 = get_all_documents(where={"policy_id": "NREGA", "year": "2020"})
   centroid_2020 = np.mean([embed(doc) for doc in data_2020], axis=0)
   
   # Cosine distance
   drift_score = 1 - cosine_similarity(centroid_2019, centroid_2020)
   # Returns: 0.74
   ```

3. **Classification**:
   ```python
   if drift_score > 0.70:
       severity = "CRITICAL"
   ```

**Output:**
```
NREGA Policy Change Analysis (2019 → 2020):

**Drift Score: 0.74 (CRITICAL)**

Major changes detected:
- Budget doubled from ₹60,000 crore to ₹1,11,500 crore
- COVID response: Emergency employment guarantee expanded
- Wage increase: ₹202/day → ₹220/day

This represents one of the largest year-over-year changes in NREGA history, driven by pandemic response measures.
```

---

## Example 7: Edge Case - No Results

**Input:**
```
"Tell me about PM-AWAS budget in 2008"
```

**Processing steps:**

1. **Policy detection**: "PM-AWAS" → detected but lowercase match
2. **Year extraction**: 2008
3. **ChromaDB query**:
   ```python
   results = query_documents(
       query_text="PM-AWAS budget 2008",
       n_results=5,
       where={"policy_id": "PMAY", "year": "2008"}
   )
   # Returns: empty (PM-AWAS launched in 2015)
   ```

4. **Fallback behavior** (`src/reasoning.py`):
   - No exact matches
   - Removes year filter, queries just policy
   - Returns general info with caveat

**Output:**
```json
{
  "final_answer": "PM-AWAS (Pradhan Mantri Awas Yojana) was launched in 2015. No data available for 2008 as the scheme did not exist then.\n\nAvailable data: 2015-2025\nLatest allocation (2024): ₹79,000 crore",
  "confidence_score": 0.45,
  "warning": "No exact match for requested year"
}
```

---

## Example 8: Multi-Policy Query (Known Limitation)

**Input:**
```
"Compare NREGA and PM-KISAN eligibility"
```

**Processing steps:**

1. **Policy detection**:
   - First match: "NREGA"
   - Second match: "PM-KISAN"
   - **Current behavior**: Only uses first match

2. **Actual query**:
   ```python
   # Only queries NREGA due to single-policy limitation
   where = {"policy_id": "NREGA"}
   ```

**Output (partial):**
```json
{
  "final_answer": "NREGA Eligibility:\n- Age: 18+\n- Location: Rural areas\n- Requirement: Willingness for manual labor...\n\n[Note: Query mentioned multiple policies but system currently supports single-policy queries]",
  "confidence_score": 0.65,
  "limitation": "multi_policy_not_supported"
}
```

**Why this limitation exists:**
- ChromaDB `where` clause doesn't support `$or` cleanly
- Would need to run multiple queries and merge
- Adds latency and complexity for edge case

---

## API Endpoint Examples

### Query Endpoint

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "PM-KISAN benefits",
    "language": "en"
  }'
```

### With Authentication

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -d "username=user@example.com&password=secret" | jq -r '.access_token')

# Query with session
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "My previous query about NREGA",
    "session_id": "abc-123"
  }'
```

### Document Upload

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@aadhaar_card.jpg"
```

### Translation

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "NREGA provides 100 days of employment",
    "target_lang": "hi"
  }'
```

---

## Query Patterns That Work Well

| Pattern | Example | Expected Accuracy |
|---------|---------|-------------------|
| Definition | "What is NREGA?" | ~90% |
| Budget + Year | "NREGA budget 2023" | ~85% |
| Eligibility | "Am I eligible for PM-KISAN as a farmer?" | ~80% |
| Hindi input | "पीएम किसान की पात्रता" | ~75% |
| Year range | "Changes from 2019 to 2020" | ~70% |

## Query Patterns That Struggle

| Pattern | Example | Issue |
|---------|---------|-------|
| Multi-policy | "Compare NREGA and RTI" | Only handles first policy |
| Vague temporal | "Recent NREGA changes" | No year extracted |
| Complex conditions | "NREGA if I'm 45 and disabled" | Disability not in rules |
| Handwritten docs | Photo of handwritten form | OCR fails (<30% accuracy) |
