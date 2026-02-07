"""
AI-powered document checker for PolicyPulse.

Features:
- OCR text extraction from uploaded images
- Document type classification
- Field extraction and validation
- Scheme requirement matching
"""

import re
import logging
from typing import Dict, List, Optional, Any
from PIL import Image, ImageEnhance
import pytesseract
from io import BytesIO

logger = logging.getLogger(__name__)

# OCR quality is... variable. Hindi works ok, Tamil is rough
# might need to add tesseract language packs per deployment


# Document type patterns
DOCUMENT_PATTERNS = {
    'aadhaar': {
        'keywords': ['aadhaar', 'आधार', 'government of india', 'unique identification'],
        'number_pattern': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        'required_fields': ['name', 'aadhaar_number', 'dob']
        # VID is sometimes present but we don't extract it yet
    },
    'income_certificate': {
        'keywords': ['income', 'certificate', 'आय प्रमाण', 'annual income'],
        'number_pattern': r'(?:Rs\.?|₹)\s?(\d+(?:,\d+)*)',
        'required_fields': ['name', 'income', 'issue_date']
    },
    'land_record': {
        'keywords': ['patta', 'chitta', 'survey', 'land record', 'भूमि'],
        'number_pattern': r'survey\s*no[\.:]?\s*(\d+)',
        'required_fields': ['owner_name', 'survey_number', 'area']
    },
    'ration_card': {
        'keywords': ['ration', 'राशन', 'bpl', 'apl', 'food'],
        'number_pattern': r'\b\d{10,12}\b',
        'required_fields': ['card_type', 'card_number', 'family_members']
    }
    # NOTE: we tested with caste certificates too but accuracy was <60%
    # would need more training data to add
}


# Scheme document requirements
SCHEME_REQUIREMENTS = {
    'NREGA': {
        'required': ['aadhaar', 'ration_card'],
        'optional': ['land_record']
    },
    'PM-KISAN': {
        'required': ['aadhaar', 'land_record'],
        'optional': ['income_certificate']
    },
    'AYUSHMAN_BHARAT': {
        'required': ['aadhaar', 'ration_card'],
        'optional': ['income_certificate']
    },
    'RTI': {
        'required': ['aadhaar'],
        'optional': []
    }
}


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR accuracy.
    - Convert to grayscale
    - Increase contrast
    - Sharpen
    """
    # 1. Grayscale
    image = image.convert('L')
    
    # 2. Enhance Contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)  # Increase contrast
    
    # 3. Sharpen
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.5) # Sharpen slightly
    
    # 4. Resize if too small (heuristic)
    if image.width < 1000:
        ratio = 2.0
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        
    return image

def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extract text from image using OCR with preprocessing.
    
    Args:
        image_bytes: Image file as bytes
    
    Returns:
        Extracted text
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        
        # Preprocess
        processed_image = preprocess_image(image)
        
        # Extract text (English + Hindi)
        # Assuming tesseract is installed and in path or configured
        # custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed_image, lang='eng+hin')
        
        logger.info(f"Extracted {len(text)} characters from image after preprocessing")
        return text.strip()
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise


def detect_document_type(text: str) -> Optional[str]:
    """
    Detect document type from extracted text.
    
    Args:
        text: Extracted OCR text
    
    Returns:
        Document type or None
    """
    text_lower = text.lower()
    
    # Count keyword matches for each document type
    scores = {}
    for doc_type, patterns in DOCUMENT_PATTERNS.items():
        score = sum(1 for keyword in patterns['keywords'] if keyword in text_lower)
        if score > 0:
            scores[doc_type] = score
    
    if not scores:
        return None
    
    # Return type with highest score
    detected_type = max(scores, key=scores.get)
    logger.info(f"Detected document type: {detected_type} (score: {scores[detected_type]})")
    
    return detected_type


def extract_fields(text: str, doc_type: str) -> Dict[str, Any]:
    """
    Extract specific fields based on document type.
    
    Args:
        text: OCR text
        doc_type: Document type
    
    Returns:
        Dict of extracted fields
    """
    fields = {}
    
    if doc_type == 'aadhaar':
        # Extract Aadhaar number (12 digits)
        pattern = DOCUMENT_PATTERNS['aadhaar']['number_pattern']
        matches = re.findall(pattern, text)
        if matches:
            # Take the first 12-digit number found
            for match in matches:
                cleaned = match.replace(' ', '')
                if len(cleaned) == 12:
                    fields['aadhaar_number'] = cleaned
                    break
        
        # Extract DOB - try multiple formats
        # Extract DOB - try multiple formats
        # Format 1: DD/MM/YYYY
        dob_match = re.search(r'\b(\d{2}[/]\d{2}[/]\d{4})\b', text)
        if dob_match:
            fields['dob'] = dob_match.group(1)
        else:
            # Format 2: DD-MM-YYYY
            dob_match = re.search(r'\b(\d{2}-\d{2}-\d{4})\b', text)
            if dob_match:
                fields['dob'] = dob_match.group(1)
            else:
                # Format 3: Look for "DOB" or "Birth" keywords with relaxed spacing
                dob_match = re.search(r'(?:DOB|Birth|Date of Birth|जन्म)[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
                if dob_match:
                    fields['dob'] = dob_match.group(1)
                else:
                    # Format 4: Year of Birth (YOB) only - common on new Aadhaar
                    yob_match = re.search(r'(?:Year of Birth|YOB|Year|वर्ष)[:\s-]*(\d{4})', text, re.IGNORECASE)
                    if yob_match:
                         fields['dob'] = f"01/01/{yob_match.group(1)}" # Default to Jan 1st
                         
        # Calculate age from DOB
        if 'dob' in fields:
            try:
                from datetime import datetime
                dob_str = fields['dob']
                today = datetime.now()
                
                # Parse date (handle both / and -)
                if '/' in dob_str:
                    dob_date = datetime.strptime(dob_str, '%d/%m/%Y')
                elif '-' in dob_str:
                    dob_date = datetime.strptime(dob_str, '%d-%m-%Y')
                
                age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                fields['age'] = age
            except:
                pass
        
        # Extract name - improved logic to avoid official text
        # Blacklist of words to exclude from names
        exclude_words = ['government', 'india', 'unique', 'identification', 'authority', 
                        'aadhaar', 'आधार', 'भारत', 'सरकार', 'पहचान', 'प्राधिकरण']
        
        # Look for "To" keyword first (most reliable)
        name_match = re.search(r'To\s*\n\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,2})', text, re.MULTILINE)
        if name_match:
            potential_name = name_match.group(1).strip()
            # Check if name contains blacklisted words
            if not any(word.lower() in potential_name.lower() for word in exclude_words):
                fields['name'] = potential_name
        
        # If no name yet, look after S/O, D/O, W/O (handle OCR errors)
        if 'name' not in fields:
            # Try multiple patterns for OCR errors (S/O, SIO, SiO, etc.)
            so_patterns = [
                r'S/O\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
                r'SIO\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
                r'SiO\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
                r'D/O\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
                r'W/O\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)'
            ]
            
            for pattern in so_patterns:
                name_match = re.search(pattern, text)
                if name_match:
                    parent_name = name_match.group(1).strip()
                    # The actual person's name is usually before S/O in the same section
                    # Look for text before the S/O pattern
                    so_index = text.find(name_match.group(0))
                    if so_index > 0:
                        # Get text before S/O (within 200 chars)
                        before_text = text[max(0, so_index-200):so_index]
                        # Find last capitalized name before S/O
                        potential_names = re.findall(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', before_text)
                        if potential_names:
                            # Take the last match (closest to S/O)
                            for pname in reversed(potential_names):
                                if not any(word.lower() in pname.lower() for word in exclude_words):
                                    if pname != parent_name:  # Make sure it's not the parent's name
                                        fields['name'] = pname
                                        break
                    if 'name' in fields:
                        break
        
        # Try extracting name from address if it contains S/O format
        if 'name' not in fields and 'address' in fields:
            # Pattern: "Name\nS/O Parent Name" (handle OCR errors: SIO, SiO, S/O)
            addr_name_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[,\s]*S[/Ii]?O', fields['address'])
            if addr_name_match:
                potential_name = addr_name_match.group(1).strip()
                if not any(word.lower() in potential_name.lower() for word in exclude_words):
                    fields['name'] = potential_name
        
        # Fallback: Find name near enrollment number
        if 'name' not in fields:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'enrollment' in line.lower() and i + 1 < len(lines):
                    # Next line after enrollment might have name
                    for j in range(i+1, min(i+4, len(lines))):
                        potential_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b', lines[j])
                        if potential_names:
                            for pname in potential_names:
                                if not any(word.lower() in pname.lower() for word in exclude_words):
                                    fields['name'] = pname
                                    break
                        if 'name' in fields:
                            break
                    if 'name' in fields:
                        break
        
        # Extract address and determine locality
        address_match = re.search(r'(?:Address|पता)[:\s]*\n(.+?)(?:\n\n|District|PIN|$)', text, re.IGNORECASE | re.DOTALL)
        if address_match:
            address = address_match.group(1).strip()
            fields['address'] = address[:200]  # Limit length
            
            # Determine locality type
            urban_keywords = ['city', 'nagar', 'colony', 'sector', 'apartment', 'flat', 'tower']
            rural_keywords = ['village', 'gram', 'gaon', 'tehsil', 'post']
            
            address_lower = address.lower()
            if any(keyword in address_lower for keyword in urban_keywords):
                fields['locality'] = 'urban'
            elif any(keyword in address_lower for keyword in rural_keywords):
                fields['locality'] = 'rural'
            else:
                # Default: if PIN code area suggests urban (metro cities)
                pin_match = re.search(r'\b(11\d{4}|40\d{4}|56\d{4}|60\d{4})\b', text)
                if pin_match:
                    fields['locality'] = 'urban'
                else:
                    fields['locality'] = 'unknown'
        
        # Extract Gender
        # Look for Male/Female/Transgender keywords
        # Common formats: "Male", "MALE", "Female", "FEMALE", "पुरुष", "महिला"
        gender_match = re.search(r'\b(Male|Female|Transgender|MALE|FEMALE)\b', text, re.IGNORECASE)
        if gender_match:
            raw_gender = gender_match.group(1).lower()
            if 'female' in raw_gender:
                fields['gender'] = 'female'
            elif 'male' in raw_gender:
                fields['gender'] = 'male'
            elif 'transgender' in raw_gender:
                fields['gender'] = 'transgender'
        else:
            # Try Hindi
            if 'महिला' in text:
                fields['gender'] = 'female'
            elif 'पुरुष' in text:
                fields['gender'] = 'male'
    
    elif doc_type == 'income_certificate':
        # Extract income amount
        pattern = DOCUMENT_PATTERNS['income_certificate']['number_pattern']
        match = re.search(pattern, text)
        if match:
            income_str = match.group(1).replace(',', '')
            fields['income'] = int(income_str)
        
        # Extract year
        year_match = re.search(r'20\d{2}', text)
        if year_match:
            fields['issue_year'] = year_match.group(0)
    
    elif doc_type == 'land_record':
        # Extract survey number
        pattern = DOCUMENT_PATTERNS['land_record']['number_pattern']
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields['survey_number'] = match.group(1)
        
        # Extract area (acres/hectares)
        area_match = re.search(r'(\d+\.?\d*)\s*(acre|hectare|ha)', text, re.IGNORECASE)
        if area_match:
            fields['area'] = f"{area_match.group(1)} {area_match.group(2)}"
    
    elif doc_type == 'ration_card':
        # Extract card number
        pattern = DOCUMENT_PATTERNS['ration_card']['number_pattern']
        match = re.search(pattern, text)
        if match:
            fields['card_number'] = match.group(0)
        
        # Detect card type (BPL/APL)
        if 'bpl' in text.lower():
            fields['card_type'] = 'BPL'
        elif 'apl' in text.lower():
            fields['card_type'] = 'APL'
    
    logger.info(f"Extracted fields for {doc_type}: {list(fields.keys())}")
    return fields


def validate_document(doc_type: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted document fields.
    
    Args:
        doc_type: Document type
        fields: Extracted fields
    
    Returns:
        Validation result with status and issues
    """
    validation = {
        'valid': True,
        'issues': [],
        'completeness': 0.0
    }
    
    required_fields = DOCUMENT_PATTERNS[doc_type]['required_fields']
    
    # Check for required fields
    missing_fields = [f for f in required_fields if f not in fields]
    if missing_fields:
        validation['issues'].append(f"Could not extract: {', '.join(missing_fields)}")
        # Only mark invalid if critical field is missing
        if doc_type == 'aadhaar' and 'aadhaar_number' not in fields:
            validation['valid'] = False
        elif doc_type == 'income_certificate' and 'income' not in fields:
            validation['valid'] = False
        # Otherwise, document is still considered valid
    
    # Calculate completeness
    extraction_rate = len([f for f in required_fields if f in fields]) / len(required_fields)
    validation['completeness'] = round(extraction_rate * 100, 1)
    
    # Type-specific validation
    if doc_type == 'aadhaar' and 'aadhaar_number' in fields:
        number = fields['aadhaar_number']
        if len(number) != 12 or not number.isdigit():
            validation['issues'].append("Invalid Aadhaar number format")
            validation['valid'] = False
    
    if doc_type == 'income_certificate' and 'income' in fields:
        if fields['income'] <= 0:
            validation['issues'].append("Invalid income amount")
            validation['valid'] = False
    
    logger.info(f"Validation result: {validation['valid']}, completeness: {validation['completeness']}%")
    return validation


def check_scheme_requirements(user_documents: List[str], eligible_schemes: List[str]) -> Dict[str, Any]:
    """
    Check which scheme requirements are met by user's documents.
    
    Args:
        user_documents: List of document types user has
        eligible_schemes: List of schemes user is eligible for
    
    Returns:
        Dict with scheme-wise document status
    """
    results = {}
    
    for scheme in eligible_schemes:
        if scheme not in SCHEME_REQUIREMENTS:
            continue
        
        requirements = SCHEME_REQUIREMENTS[scheme]
        required_docs = requirements['required']
        optional_docs = requirements['optional']
        
        # Check required documents
        missing_required = [doc for doc in required_docs if doc not in user_documents]
        has_optional = [doc for doc in optional_docs if doc in user_documents]
        
        status = 'complete' if not missing_required else 'incomplete'
        
        results[scheme] = {
            'status': status,
            'missing_required': missing_required,
            'has_optional': has_optional,
            'ready_to_apply': status == 'complete'
        }
    
    logger.info(f"Checked requirements for {len(eligible_schemes)} schemes")
    return results


def process_document(image_bytes: bytes) -> Dict[str, Any]:
    """
    Complete document processing pipeline.
    
    Args:
        image_bytes: Uploaded image
    
    Returns:
        Processing result with all extracted info
    """
    result = {
        'success': False,
        'document_type': None,
        'extracted_fields': {},
        'validation': {},
        'ocr_text': ''
    }
    
    try:
        # Step 1: OCR
        text = extract_text_from_image(image_bytes)
        result['ocr_text'] = text[:500]  # First 500 chars for preview
        
        # Step 2: Detect document type
        doc_type = detect_document_type(text)
        if not doc_type:
            result['success'] = False
            result['error'] = "Could not identify document type. Please upload a clear photo."
            return result
        
        result['document_type'] = doc_type
        
        # Step 3: Extract fields
        fields = extract_fields(text, doc_type)
        result['extracted_fields'] = fields
        
        # Step 4: Validate
        validation = validate_document(doc_type, fields)
        result['validation'] = validation
        
        result['success'] = True
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        result['error'] = f"Processing error: {str(e)}"
    
    return result
