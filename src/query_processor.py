"""
Query Processor module for intelligent query understanding.

Extracts policy mentions, years, and query intent to improve retrieval accuracy.
Handles Hindi/English policy names and year range queries.
"""

import re
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

# Policy name mappings (English + Hindi + common variations)
POLICY_ALIASES = {
    'nrega': 'NREGA',
    'mgnrega': 'NREGA',
    'एनआरेगा': 'NREGA',
    'मनरेगा': 'NREGA',
    'नरेगा': 'NREGA',
    'mnrega': 'NREGA',
    'mahatma gandhi': 'NREGA',
    'employment guarantee': 'NREGA',
    'रोजगार गारंटी': 'NREGA',
    'ந்ரேகா': 'NREGA', # Tamil
    'தேசிய ஊரக வேலை உறுதி': 'NREGA', # Tamil (National Rural Employment Guarantee)
    'ഗ്രാമീണ തൊഴിലുറപ്പ്': 'NREGA', # Malayalam
    'ಉದ್ಯೋಗ ಖಾತರಿ': 'NREGA', # Kannada
    'ఉపాధి హామీ': 'NREGA', # Telugu (for good measure)
    
    # RTI
    'rti': 'RTI',
    'right to information': 'RTI',
    'सूचना का अधिकार': 'RTI',
    'आरटीआई': 'RTI',
    
    # PM-KISAN
    'pm-kisan': 'PM-KISAN',
    'pm kisan': 'PM-KISAN',
    'pmkisan': 'PM-KISAN',
    'kisan samman': 'PM-KISAN',
    'किसान सम्मान': 'PM-KISAN',
    'पीएम किसान': 'PM-KISAN',
    'प्रधानमंत्री किसान': 'PM-KISAN',
    
    # Ayushman Bharat
    'ayushman': 'AYUSHMAN-BHARAT',
    'ayushman bharat': 'AYUSHMAN-BHARAT',
    'आयुष्मान': 'AYUSHMAN-BHARAT',
    'आयुष्मान भारत': 'AYUSHMAN-BHARAT',
    'pmjay': 'AYUSHMAN-BHARAT',
    
    # Swachh Bharat
    'swachh bharat': 'SWACHH-BHARAT',
    'swachh': 'SWACHH-BHARAT',
    'स्वच्छ भारत': 'SWACHH-BHARAT',
    'स्वच्छ': 'SWACHH-BHARAT',
    'clean india': 'SWACHH-BHARAT',
    
    # Digital India
    'digital india': 'DIGITAL-INDIA',
    'डिजिटल इंडिया': 'DIGITAL-INDIA',
    'डिजिटल भारत': 'DIGITAL-INDIA',
    
    # Make in India
    'make in india': 'MAKE-IN-INDIA',
    'मेक इन इंडिया': 'MAKE-IN-INDIA',
    
    # Skill India
    'skill india': 'SKILL-INDIA',
    'स्किल इंडिया': 'SKILL-INDIA',
    'कौशल भारत': 'SKILL-INDIA',
    'कौशल विकास': 'SKILL-INDIA',
    
    # Smart Cities
    'smart city': 'SMART-CITIES',
    'smart cities': 'SMART-CITIES',
    'स्मार्ट सिटी': 'SMART-CITIES',
    
    # NEP
    'nep': 'NEP',
    'education policy': 'NEP',
    'national education': 'NEP',
    'शिक्षा नीति': 'NEP',
    'राष्ट्रीय शिक्षा': 'NEP',
}


def detect_policy_from_query(query: str) -> Optional[str]:
    """
    Detect which policy the query is about.
    
    Args:
        query: User's question (English or Hindi)
        
    Returns:
        Policy ID (e.g., 'NREGA') or None if not detected
    """
    query_lower = query.lower()
    
    # Check for exact/partial matches
    for alias, policy_id in POLICY_ALIASES.items():
        if alias in query_lower:
            logger.info(f"Detected policy '{policy_id}' from alias '{alias}'")
            return policy_id
    
    return None


def extract_years_from_query(query: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract year or year range from query.
    
    Examples:
        "what changed in 2010" -> (2010, 2010)
        "between 2010 and 2012" -> (2010, 2012)
        "from 2015 to 2020" -> (2015, 2020)
        "in 2020" -> (2020, 2020)
        
    Returns:
        Tuple of (start_year, end_year) or (None, None) if no years found
    """
    # Pattern for year ranges
    range_patterns = [
        r'between\s+(\d{4})\s+(?:and|to|&)\s+(\d{4})',
        r'from\s+(\d{4})\s+(?:to|and|till|until)\s+(\d{4})',
        r'(\d{4})\s*[-–]\s*(\d{4})',
        r'(\d{4})\s+(?:to|and)\s+(\d{4})',
    ]
    
    for pattern in range_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            year1, year2 = int(match.group(1)), int(match.group(2))
            return (min(year1, year2), max(year1, year2))
    
    # Pattern for single year
    single_year = re.search(r'\b(19\d{2}|20\d{2})\b', query)
    if single_year:
        year = int(single_year.group(1))
        return (year, year)
    
    return (None, None)


def extract_demographics(query: str) -> Dict[str, Any]:
    """
    Extract demographic information from query.
    
    Returns:
        Dict with keys: age, gender, category, occupation, location_type
    """
    demographics = {}
    query_lower = query.lower()
    
    # 1. Age extraction
    # patterns: "19 year old", "19yo", "age 19", "19 years", "19 yrs"
    # Added: 'age 20', '20 age'
    age_patterns = [
        r'\b(\d{1,2})\s*(?:years?|yrs?|yo|age)\b', # 19 years, 19 age
        r'\bage\s*(\d{1,2})\b' # age 19
    ]
    
    for pattern in age_patterns:
        age_match = re.search(pattern, query_lower)
        if age_match:
            try:
                demographics['age'] = int(age_match.group(1))
                break # Stop after first match
            except ValueError:
                pass
            
    # 2. Gender extraction
    if any(w in query_lower for w in ['female', 'woman', 'girl', 'lady']):
        demographics['gender'] = 'female'
    elif any(w in query_lower for w in ['male', 'man', 'boy', 'gentleman']):
        demographics['gender'] = 'male'
        
    # 3. Category extraction
    # Use word boundaries for short acronyms
    if re.search(r'\b(sc|scheduled caste)\b', query_lower):
        demographics['category'] = 'sc'
    elif re.search(r'\b(st|scheduled tribe)\b', query_lower):
        demographics['category'] = 'st'
    elif re.search(r'\b(obc|backward class)\b', query_lower):
        demographics['category'] = 'obc'
    elif 'general' in query_lower:
        demographics['category'] = 'general'
        
    # 4. Occupation extraction
    occupations = {
        'farmer': ['farmer', 'agriculture', 'kisan'],
        'student': ['student', 'studying', 'college', 'school'],
        'entrepreneur': ['entrepreneur', 'business', 'startup', 'founder'],
        'unemployed': ['unemployed', 'jobless'],
        'worker': ['worker', 'laborer', 'labourer']
    }
    
    for occ, keywords in occupations.items():
        if any(k in query_lower for k in keywords):
            demographics['occupation'] = occ
            break
            
    # 5. Location extraction
    if 'rural' in query_lower or 'village' in query_lower:
        demographics['location_type'] = 'rural'
    elif 'urban' in query_lower or 'city' in query_lower or 'town' in query_lower:
        demographics['location_type'] = 'urban'
        
    return demographics


def build_query_filter(
    policy_id: Optional[str] = None,
    year_start: Optional[int] = None,
    year_end: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Build ChromaDB where filter from detected parameters.
    
    Args:
        policy_id: Detected policy (e.g., 'NREGA')
        year_start: Start year for filtering
        year_end: End year for filtering
        
    Returns:
        Dict filter for ChromaDB query, or None if no filters
    """
    filters = []
    
    if policy_id:
        filters.append({"policy_id": policy_id})
    
    if year_start and year_end:
        if year_start == year_end:
            # Single year - ChromaDB stores years as strings!
            filters.append({"year": str(year_start)})
        else:
            # Year range - need to filter by string years
            # Generate list of years in range and use $in operator
            year_list = [str(y) for y in range(year_start, year_end + 1)]
            filters.append({"year": {"$in": year_list}})
    
    if not filters:
        return None
    
    if len(filters) == 1:
        return filters[0]
    
    # Multiple filters - use $and
    return {"$and": filters}


def process_query(query: str, original_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Process query to extract all relevant parameters.
    
    Args:
        query: User's question (translated to English if applicable)
        original_query: Original user question (before translation, to catch native entity names)
        
    Returns:
        Dict with:
            - policy_id: Detected policy or None
            - year_start: Start year or None
            - year_end: End year or None
            - filter: ChromaDB where filter or None
            - enhanced_query: Query text (may be enhanced for better retrieval)
            - demographics: Dict of extracted user profile info
    """
    policy_id = detect_policy_from_query(query)
    
    # Fallback: Check original text if translation missed the policy name
    # (e.g. Tamil "NREGA" -> English "Nreka" which fails match, but "ந்ரேகா" matches alias)
    if not policy_id and original_query:
        policy_id = detect_policy_from_query(original_query)
        if policy_id:
            logger.info(f"Detected policy '{policy_id}' from original query text")

    year_start, year_end = extract_years_from_query(query)
    demographics = extract_demographics(query)
    
    filter_dict = build_query_filter(policy_id, year_start, year_end)
    
    result = {
        "policy_id": policy_id,
        "year_start": year_start,
        "year_end": year_end,
        "filter": filter_dict,
        "enhanced_query": query,
        "demographics": demographics
    }
    
    logger.info(f"Query processed: policy={policy_id}, demographics={demographics}")
    return result


# Quick test
if __name__ == "__main__":
    test_queries = [
        "what is nrega",
        "suggest policies for 19 year old general male",
        "I am a farmer looking for loans",
        "scholarships for sc students in urban areas",
        "PM-KISAN budget in 2020",
    ]
    
    print("Testing query processor:")
    for q in test_queries:
        result = process_query(q)
        print(f"\n'{q[:40]}...'")
        print(f"  Policy: {result['policy_id']}")
        print(f"  Years: {result['year_start']} - {result['year_end']}")
        print(f"  Demographics: {result['demographics']}")
