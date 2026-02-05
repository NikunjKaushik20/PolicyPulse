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
    # NREGA
    'nrega': 'NREGA',
    'mgnrega': 'NREGA',
    'एनआरेगा': 'NREGA',
    'मनरेगा': 'NREGA',
    'नरेगा': 'NREGA',
    'mnrega': 'NREGA',
    'mahatma gandhi': 'NREGA',
    'employment guarantee': 'NREGA',
    'रोजगार गारंटी': 'NREGA',
    
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
            # Single year
            filters.append({"year": year_start})
        else:
            # Year range - ChromaDB uses $gte/$lte
            filters.append({"year": {"$gte": year_start}})
            filters.append({"year": {"$lte": year_end}})
    
    if not filters:
        return None
    
    if len(filters) == 1:
        return filters[0]
    
    # Multiple filters - use $and
    return {"$and": filters}


def process_query(query: str) -> Dict[str, Any]:
    """
    Process query to extract all relevant parameters.
    
    Args:
        query: User's question
        
    Returns:
        Dict with:
            - policy_id: Detected policy or None
            - year_start: Start year or None
            - year_end: End year or None
            - filter: ChromaDB where filter or None
            - enhanced_query: Query text (may be enhanced for better retrieval)
    """
    policy_id = detect_policy_from_query(query)
    year_start, year_end = extract_years_from_query(query)
    
    filter_dict = build_query_filter(policy_id, year_start, year_end)
    
    result = {
        "policy_id": policy_id,
        "year_start": year_start,
        "year_end": year_end,
        "filter": filter_dict,
        "enhanced_query": query
    }
    
    logger.info(f"Query processed: policy={policy_id}, years={year_start}-{year_end}")
    return result


# Quick test
if __name__ == "__main__":
    test_queries = [
        "what is nrega",
        "एनआरेगा क्या है?",
        "what changed in nrega between 2010 and 2012",
        "PM-KISAN budget in 2020",
        "आयुष्मान भारत के बारे में बताओ",
        "what was the news about RTI in 2019",
    ]
    
    print("Testing query processor:")
    for q in test_queries:
        result = process_query(q)
        print(f"\n'{q[:40]}...'")
        print(f"  Policy: {result['policy_id']}")
        print(f"  Years: {result['year_start']} - {result['year_end']}")
        print(f"  Filter: {result['filter']}")
