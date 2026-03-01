"""
Text-to-Speech module for voice interface.

Primary: Sarvam AI Bulbul v3 — high-quality Indian language TTS (10 languages)
Fallback: Google Text-to-Speech (gTTS) — free, lower quality

Sarvam AI API:
  - Endpoint: POST https://api.sarvam.ai/text-to-speech
  - Auth header: api-subscription-key
  - Model: bulbul:v3 (30+ voices, code-mixed text support)
  - Returns base64-encoded WAV audio
  - Max 2500 characters per request
"""

import os
import re
import base64
import logging
import requests
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Sarvam AI Configuration ──────────────────────────────────────────────────

SARVAM_API_KEY = os.getenv("SARVAM_AI_API_KEY", "")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_MODEL = "bulbul:v2"  # v2 is 3x faster than v3
SARVAM_MAX_CHARS = 500  # API enforces 500 chars per input string for all models

# Sarvam language codes (BCP-47 format)
SARVAM_LANGUAGES = {
    'en': 'en-IN',
    'hi': 'hi-IN',
    'ta': 'ta-IN',
    'te': 'te-IN',
    'bn': 'bn-IN',
    'mr': 'mr-IN',
    'gu': 'gu-IN',
    'kn': 'kn-IN',
    'ml': 'ml-IN',
    'pa': 'pa-IN',
}

# Default speakers per language for natural sound
# Using Sarvam Bulbul v3 voices
# bulbul:v2 speakers: Female: anushka, manisha, vidya, arya | Male: abhilash, karun, hitesh
SARVAM_SPEAKERS = {
    'hi': 'manisha',    # Hindi
    'en': 'manisha',    # English
    'ta': 'manisha',    # Tamil
    'te': 'manisha',    # Telugu
    'bn': 'manisha',    # Bengali
    'mr': 'manisha',    # Marathi
    'gu': 'manisha',    # Gujarati
    'kn': 'manisha',    # Kannada
    'ml': 'manisha',    # Malayalam
    'pa': 'manisha',    # Punjabi
}


# ── gTTS Fallback Configuration ──────────────────────────────────────────────

try:
    from gtts import gTTS
    gtts_available = True
except ImportError:
    gtts_available = False
    logger.warning("gTTS not installed — fallback TTS unavailable")

GTTS_LANGUAGES = {
    'en': 'en', 'hi': 'hi', 'ta': 'ta', 'te': 'te', 'bn': 'bn',
    'mr': 'mr', 'gu': 'gu', 'kn': 'kn', 'ml': 'ml', 'pa': 'pa',
}


# ── Text chunking helper ─────────────────────────────────────────────────────

def _chunk_text(text: str, max_len: int = 500) -> list:
    """
    Split long text into chunks of <= max_len characters.
    Tries to split at sentence boundaries (. ! ? newline) first,
    falls back to splitting at spaces.
    """
    if len(text) <= max_len:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break

        # Try to find a sentence boundary within the limit
        split_pos = -1
        for sep in ['. ', '\u0964 ', '? ', '! ', '\n']:
            pos = remaining.rfind(sep, 0, max_len)
            if pos > split_pos:
                split_pos = pos + len(sep)

        # No sentence boundary -- try splitting at a space
        if split_pos <= 0:
            split_pos = remaining.rfind(' ', 0, max_len)

        # No space either -- hard cut
        if split_pos <= 0:
            split_pos = max_len

        chunk = remaining[:split_pos].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_pos:].strip()

    return chunks


# ── Sarvam AI TTS (Primary) ─────────────────────────────────────────────────

def sarvam_text_to_speech(
    text: str,
    lang: str = 'hi',
    speaker: str = None,
    pace: float = 1.0,
) -> bytes:
    """
    Convert text to speech using Sarvam AI Bulbul v3 model.
    Automatically chunks long text into <=500 char segments.

    Args:
        text: Text to convert (any length, auto-chunked)
        lang: Language code ('hi', 'en', 'ta', etc.)
        speaker: Voice name (default: auto-selected per language)
        pace: Speech speed (0.5-2.0, default 1.0)
        temperature: Expressiveness (0.01-2.0, default 0.6)

    Returns:
        Audio bytes (WAV format) or empty bytes on failure
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for Sarvam TTS")
        return b''

    if not SARVAM_API_KEY:
        logger.warning("SARVAM_AI_API_KEY not set -- cannot use Sarvam TTS")
        return b''

    # Resolve language and speaker
    target_lang = SARVAM_LANGUAGES.get(lang.lower(), 'hi-IN')
    if speaker is None:
        speaker = SARVAM_SPEAKERS.get(lang.lower(), 'manisha')

    # Chunk the text into <=500 char segments
    chunks = _chunk_text(text, SARVAM_MAX_CHARS)
    logger.info(f"Sarvam TTS: {len(text)} chars, {len(chunks)} chunk(s)")

    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }

    # Sarvam allows max 3 inputs per API call
    # Batch chunks into groups of 3
    BATCH_SIZE = 3
    all_audio = b''

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start:batch_start + BATCH_SIZE]

        try:
            payload = {
                "inputs": batch,
                "target_language_code": target_lang,
                "speaker": speaker,
                "model": SARVAM_MODEL,
                "pace": pace,
            }

            response = requests.post(
                SARVAM_TTS_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                audios = data.get("audios", [])
                for audio_b64 in audios:
                    if audio_b64:
                        all_audio += base64.b64decode(audio_b64)
            else:
                logger.error(f"Sarvam TTS failed [{response.status_code}]: {response.text[:200]}")
                return b''

        except requests.exceptions.Timeout:
            logger.error("Sarvam TTS batch timed out (30s)")
            return b''
        except Exception as e:
            logger.error(f"Sarvam TTS error: {e}")
            return b''

    if all_audio:
        logger.info(
            f"Sarvam TTS done: {len(text)} chars -> {len(all_audio)} bytes "
            f"({target_lang}, speaker={speaker}, chunks={len(chunks)})"
        )
    return all_audio


# ── gTTS Fallback ────────────────────────────────────────────────────────────

def _gtts_fallback(text: str, lang: str = 'hi', slow: bool = False) -> bytes:
    """Fallback TTS using Google Text-to-Speech (free, lower quality)."""
    if not gtts_available:
        logger.error("gTTS not available for fallback")
        return b''

    try:
        gtts_lang = GTTS_LANGUAGES.get(lang.lower(), 'en')
        tts = gTTS(text=text, lang=gtts_lang, slow=slow)
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        logger.info(f"gTTS fallback: {len(text)} chars in {gtts_lang}")
        return audio_buffer.read()
    except Exception as e:
        logger.error(f"gTTS fallback failed: {e}")
        return b''


# ── Text Cleaning for Speech ─────────────────────────────────────────────────

def _clean_text_for_speech(text: str) -> str:
    """
    Strip markdown, JSON, and special characters so TTS reads naturally.
    Converts '**bold**' -> 'bold', removes ```code blocks```, links, etc.
    """
    # Remove code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    # Remove inline code (`...`)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    # Remove markdown images ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', text)
    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    # Remove markdown headers (## Header -> Header)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # Remove bullet points and numbered lists
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Remove JSON-like blocks { ... }
    text = re.sub(r'\{[^}]{20,}\}', ' ', text)
    # Remove horizontal rules (--- or ***)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove remaining special chars that sound bad when read aloud
    text = re.sub(r'[#|>~\\]', ' ', text)
    # Collapse multiple spaces/newlines into single space
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── Main TTS Function (Sarvam -> gTTS fallback) ──────────────────────────────

def text_to_speech(text: str, lang: str = 'hi', slow: bool = False) -> bytes:
    """
    Convert text to speech audio.
    Cleans markdown/JSON before speaking.

    Uses Sarvam AI Bulbul v2 as primary TTS (high-quality Indian voices).
    Falls back to gTTS if Sarvam is unavailable or fails.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for TTS")
        return b''

    # Clean markdown, JSON, special chars
    text = _clean_text_for_speech(text)
    if not text:
        return b''

    # Try Sarvam AI first
    if SARVAM_API_KEY:
        pace = 0.7 if slow else 1.0
        audio = sarvam_text_to_speech(text, lang=lang, pace=pace)
        if audio:
            return audio
        logger.warning("Sarvam TTS failed -- falling back to gTTS")

    # Fallback to gTTS
    return _gtts_fallback(text, lang=lang, slow=slow)


async def async_text_to_speech(text: str, lang: str = 'hi', slow: bool = False) -> bytes:
    """
    Async wrapper for text_to_speech — offloads the blocking API call
    to the AMD EPYC-tuned I/O thread pool.

    AMD EPYC Optimization:
      Sarvam/gTTS calls external APIs (network I/O bound). Running this on
      the EPYC I/O thread pool (sized to cores×2) prevents blocking the
      async event loop, allowing other requests to be served concurrently.
    """
    import asyncio
    from .amd_utils import get_io_thread_pool

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        get_io_thread_pool(),
        lambda: text_to_speech(text, lang=lang, slow=slow)
    )


# ── File Output ──────────────────────────────────────────────────────────────

def text_to_speech_file(text: str, output_path: str, lang: str = 'hi', slow: bool = False) -> bool:
    """
    Convert text to speech and save to file.

    Args:
        text: Text to convert
        output_path: Path to save audio file
        lang: Language code
        slow: If True, use slower speech rate

    Returns:
        True if successful, False otherwise
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for TTS")
        return False

    try:
        audio = text_to_speech(text, lang=lang, slow=slow)
        if audio:
            with open(output_path, 'wb') as f:
                f.write(audio)
            logger.info(f"Saved TTS audio to {output_path}")
            return True
        return False
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

        # Sarvam returns WAV, gTTS returns MP3
        ext = "wav" if SARVAM_API_KEY else "mp3"
        output_path = os.path.join(output_dir, f'{lang}_output.{ext}')

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
    'goodbye': 'धन्यवाद, फिर मिलेंगे',
}


def get_quick_response_audio(phrase_key: str, lang: str = 'hi') -> bytes:
    """
    Get audio for common phrases.

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
