"""
Language Detection module for automatic query language identification.

Uses langdetect for Language Identification (LID) to automatically detect
the language of user queries, eliminating the need for manual language selection.

Supports 10 Indian languages + English.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import langdetect
try:
    from langdetect import detect, detect_langs, LangDetectException
    langdetect_available = True
    logger.info("Language detection available (langdetect)")
except ImportError:
    langdetect_available = False
    logger.warning("langdetect not installed - auto language detection disabled")

# Supported languages with their ISO codes
SUPPORTED_LANGUAGES = {
    'en': 'english',
    'hi': 'hindi',
    'ta': 'tamil',
    'te': 'telugu',
    'bn': 'bengali',
    'mr': 'marathi',
    'gu': 'gujarati',
    'kn': 'kannada',
    'ml': 'malayalam',
    'pa': 'punjabi'
}

# Language names for display
LANGUAGE_NAMES = {
    'en': 'English',
    'hi': 'Hindi (हिंदी)',
    'ta': 'Tamil (தமிழ்)',
    'te': 'Telugu (తెలుగు)',
    'bn': 'Bengali (বাংলা)',
    'mr': 'Marathi (मराठी)',
    'gu': 'Gujarati (ગુજરાતી)',
    'kn': 'Kannada (ಕನ್ನಡ)',
    'ml': 'Malayalam (മലയാളം)',
    'pa': 'Punjabi (ਪੰਜਾਬੀ)'
}


def detect_language(text: str) -> Tuple[str, float]:
    """
    Detect the language of input text.
    
    Args:
        text: Input text to detect language for
        
    Returns:
        Tuple of (language_code, confidence)
        Falls back to 'en' with 0.0 confidence if detection fails
    """
    if not text or not text.strip():
        return 'en', 0.0
    
    if not langdetect_available:
        # Fallback: check for Devanagari script (Hindi/Marathi)
        return _script_based_detection(text)
    
    try:
        # Get all detected languages with probabilities
        detected = detect_langs(text)
        
        if not detected:
            return 'en', 0.0
        
        # Get the top detection
        top_lang = detected[0]
        lang_code = str(top_lang.lang)
        confidence = float(top_lang.prob)
        
        # Map to supported language or fallback to English
        if lang_code in SUPPORTED_LANGUAGES:
            logger.info(f"Detected language: {lang_code} ({confidence:.2f})")
            return lang_code, confidence
        else:
            # Unsupported language, default to English
            logger.info(f"Detected unsupported language {lang_code}, defaulting to English")
            return 'en', confidence
            
    except LangDetectException as e:
        logger.warning(f"Language detection failed: {e}")
        return _script_based_detection(text)
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        return 'en', 0.0


def _script_based_detection(text: str) -> Tuple[str, float]:
    """
    Fallback detection based on Unicode script/character ranges.
    Works offline without langdetect library.
    """
    # Count characters in different script ranges
    devanagari = 0  # Hindi, Marathi
    tamil = 0
    telugu = 0
    bengali = 0
    gujarati = 0
    kannada = 0
    malayalam = 0
    gurmukhi = 0  # Punjabi
    latin = 0
    
    for char in text:
        code = ord(char)
        if 0x0900 <= code <= 0x097F:  # Devanagari
            devanagari += 1
        elif 0x0B80 <= code <= 0x0BFF:  # Tamil
            tamil += 1
        elif 0x0C00 <= code <= 0x0C7F:  # Telugu
            telugu += 1
        elif 0x0980 <= code <= 0x09FF:  # Bengali
            bengali += 1
        elif 0x0A80 <= code <= 0x0AFF:  # Gujarati
            gujarati += 1
        elif 0x0C80 <= code <= 0x0CFF:  # Kannada
            kannada += 1
        elif 0x0D00 <= code <= 0x0D7F:  # Malayalam
            malayalam += 1
        elif 0x0A00 <= code <= 0x0A7F:  # Gurmukhi (Punjabi)
            gurmukhi += 1
        elif 0x0041 <= code <= 0x007A:  # Latin letters
            latin += 1
    
    # Find the dominant script
    script_counts = {
        'hi': devanagari,  # Could also be Marathi
        'ta': tamil,
        'te': telugu,
        'bn': bengali,
        'gu': gujarati,
        'kn': kannada,
        'ml': malayalam,
        'pa': gurmukhi,
        'en': latin
    }
    
    total = sum(script_counts.values())
    if total == 0:
        return 'en', 0.0
    
    # Get dominant language
    detected_lang = max(script_counts, key=script_counts.get)
    confidence = script_counts[detected_lang] / total
    
    logger.info(f"Script-based detection: {detected_lang} ({confidence:.2f})")
    return detected_lang, confidence


def get_language_name(lang_code: str) -> str:
    """Get display name for a language code."""
    return LANGUAGE_NAMES.get(lang_code, lang_code.upper())


def is_indian_language(lang_code: str) -> bool:
    """Check if the language code is a supported Indian language."""
    return lang_code in SUPPORTED_LANGUAGES and lang_code != 'en'


# Quick test
if __name__ == "__main__":
    test_texts = [
        ("Hello, how are you?", "en"),
        ("मुझे PM-KISAN के लिए पात्रता बताओ", "hi"),
        ("நான் எந்த திட்டங்களுக்கு தகுதியானவர்?", "ta"),
        ("నాకు అర్హత ఉన్న పథకాలు ఏవి?", "te"),
        ("আমি কোন স্কিমের জন্য যোগ্য?", "bn"),
    ]
    
    print("Testing language detection:")
    for text, expected in test_texts:
        detected, conf = detect_language(text)
        status = "✓" if detected == expected else "✗"
        print(f"{status} '{text[:30]}...' -> {detected} ({conf:.2f}) [expected: {expected}]")
