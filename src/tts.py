"""
Text-to-Speech module for voice interface.

Provides audio output in multiple languages using Google Text-to-Speech (free).
"""

import os
import logging
from io import BytesIO
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# gTTS is free and surprisingly good quality
# tested against AWS Polly, not worth the cost difference for our use case


# Language code mapping for gTTS
GTTS_LANGUAGES = {
    'en': 'en',
    'hi': 'hi',
    'ta': 'ta',
    'te': 'te',
    'bn': 'bn',
    'mr': 'mr',
    'gu': 'gu',
    'kn': 'kn',
    'ml': 'ml',
    'pa': 'pa'
    # kannada and telugu sound a bit robotic but still usable
}


def text_to_speech(text: str, lang: str = 'hi', slow: bool = False) -> bytes:
    """
    Convert text to speech audio.
    
    Args:
        text: Text to convert
        lang: Language code ('hi', 'en', etc.)
        slow: If True, use slower speech rate
    
    Returns:
        Audio bytes (MP3 format)
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for TTS")
        return b''
    
    # Normalize language code
    lang = GTTS_LANGUAGES.get(lang.lower(), 'en')
    
    try:
        # Create TTS object
        tts = gTTS(text=text, lang=lang, slow=slow)
        
        # Save to BytesIO (in-memory file)
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        logger.info(f"Generated TTS audio for {len(text)} chars in {lang}")
        return audio_buffer.read()
        
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return b''


def text_to_speech_file(text: str, output_path: str, lang: str = 'hi', slow: bool = False) -> bool:
    """
    Convert text to speech and save to file.
    
    Args:
        text: Text to convert
        output_path: Path to save audio file (e.g., 'output.mp3')
        lang: Language code
        slow: If True, use slower speech rate
    
    Returns:
        True if successful, False otherwise
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for TTS")
        return False
    
    # Normalize language code
    lang = GTTS_LANGUAGES.get(lang.lower(), 'en')
    
    try:
        # Create TTS object
        tts = gTTS(text=text, lang=lang, slow=slow)
        
        # Save to file
        tts.save(output_path)
        
        logger.info(f"Saved TTS audio to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"TTS file save failed: {e}")
        return False


def create_multilingual_audio(text_dict: dict, output_dir: str = 'audio_output') -> dict:
    """
    Create audio files in multiple languages.
    
    Args:
        text_dict: Dict mapping language codes to text
                   e.g., {'en': 'Hello', 'hi': 'नमस्ते'}
        output_dir: Directory to save audio files
    
    Returns:
        Dict mapping language codes to file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    audio_files = {}
    
    for lang, text in text_dict.items():
        if not text:
            continue
        
        output_path = os.path.join(output_dir, f'{lang}_output.mp3')
        
        if text_to_speech_file(text, output_path, lang=lang):
            audio_files[lang] = output_path
    
    return audio_files


# Pre-defined common phrases in Hindi for quick access
COMMON_PHRASES_HINDI = {
    'welcome': 'नागरिक मित्र में आपका स्वागत है',
    'searching': 'खोज रहा हूं...',
    'found_results': 'मुझे कुछ परिणाम मिले',
    'no_results': 'कोई परिणाम नहीं मिला',
    'error': 'माफ़ करें, कोई त्रुटि हुई',
    'eligible': 'आप इस योजना के लिए पात्र हैं',
    'not_eligible': 'आप इस योजना के लिए पात्र नहीं हैं',
    'goodbye': 'धन्यवाद, फिर मिलेंगे'
    # these are precomputed for faster response - not actually used yet
}


def get_quick_response_audio(phrase_key: str, lang: str = 'hi') -> bytes:
    """
    Get precomputed audio for common phrases.
    
    Args:
        phrase_key: Key from COMMON_PHRASES (e.g., 'welcome')
        lang: Language code (currently only 'hi' supported for quick responses)
    
    Returns:
        Audio bytes
    """
    if lang == 'hi' and phrase_key in COMMON_PHRASES_HINDI:
        text = COMMON_PHRASES_HINDI[phrase_key]
        return text_to_speech(text, lang='hi')
    else:
        logger.warning(f"Quick response not available for {phrase_key} in {lang}")
        return b''
