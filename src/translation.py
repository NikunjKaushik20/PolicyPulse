"""
Translation module for multilingual support using deep-translator.

Deep-translator is more reliable than googletrans and actively maintained.
Switched from googletrans after it broke in Jan 2024 (httpx version conflict).
"""

import os
import logging
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Try to import deep-translator
try:
    from deep_translator import GoogleTranslator
    translator_available = True
    logger.info("Using deep-translator (GoogleTranslator)")
except ImportError:
    translator_available = False
    logger.error("deep-translator not installed")


# Language code mapping
LANGUAGE_CODES = {
    'english': 'en',
    'hindi': 'hi',
    'tamil': 'ta',
    'telugu': 'te',
    'bengali': 'bn',
    'marathi': 'mr',
    'gujarati': 'gu',
    'kannada': 'kn',
    'malayalam': 'ml',
    'punjabi': 'pa'
    # TODO: add assamese, odia - needed for eastern states
}


def translate_text(text: str, target_lang: str = 'hi', source_lang: str = 'en') -> str:
    """
    Translate text to target language using deep-translator.
    
    Args:
        text: Text to translate
        target_lang: Target language code (e.g., 'hi' for Hindi)
        source_lang: Source language code (default: 'en')
    
    Returns:
        Translated text (or original if translation fails)
    """
    if not text or not text.strip():
        return text
    
    # Normalize language codes
    target_lang = LANGUAGE_CODES.get(target_lang.lower(), target_lang)
    source_lang = LANGUAGE_CODES.get(source_lang.lower(), source_lang)
    
    # Skip if same language
    if target_lang == source_lang:
        return text
    
    if not translator_available:
        logger.warning("Translation not available - deep-translator not installed")
        return text
    
    try:
        # Protect URLs from translation
        # Replace URLs with placeholders like ||URL1||
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        placeholders = {}
        text_to_translate = text
        
        for i, url in enumerate(urls):
            ph = f"__URL{i}__"
            placeholders[ph] = url
            text_to_translate = text_to_translate.replace(url, ph)
            
        # Use deep-translator
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text_to_translate)
        
        # Restore URLs
        if translated:
            for ph, url in placeholders.items():
                translated = translated.replace(ph, url)
                # Fallback: check for spaces or modified case (though __URL0__ is usually safe)
                # e.g. __ URL 0 __
                if ph not in translated:
                    # Try loose match if exact match fails
                    pass # TODO: Add more robust fallback if needed, but __URL0__ tested safe
            return translated
        else:
            return text
            
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text  # Return original on error


def translate_response(response: dict, target_lang: str = 'hi') -> dict:
    """
    Translate API response to target language.
    
    Args:
        response: API response dict (e.g., query result)
        target_lang: Target language code
    
    Returns:
        Response with translated fields
    """
    if target_lang == 'en':
        return response  # No translation needed
    
    try:
        translated = response.copy()
        
        # Translate final_answer field
        if 'final_answer' in translated and translated['final_answer']:
            logger.info(f"Translating final_answer to {target_lang}")
            translated['final_answer'] = translate_text(
                translated['final_answer'],
                target_lang=target_lang
            )
        
        # Translate retrieved_points content
        if 'retrieved_points' in translated and translated['retrieved_points']:
            for point in translated['retrieved_points']:
                if 'content_preview' in point and point['content_preview']:
                    point['content_preview'] = translate_text(
                        point['content_preview'],
                        target_lang=target_lang
                    )
        
        logger.info(f"Translation to {target_lang} completed")
        return translated
        
    except Exception as e:
        logger.error(f"Response translation failed: {e}")
        return response  # Return original on error


def detect_language(text: str) -> str:
    """
    Detect language of text.
    
    Args:
        text: Input text
    
    Returns:
        Language code (e.g., 'en', 'hi')
    """
    if not text or not text.strip():
        return 'en'
    
    if not translator_available:
        return 'en'
    
    try:
        # Deep-translator doesn't have built-in detection,
        # would need to use langdetect library
        # For now, return English as default
        return 'en'
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return 'en'
