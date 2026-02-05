"""
PolicyPulse REST API - Modernized with static file serving and new endpoints.

Features:
- Static file serving for new HTML/CSS/JS UI
- Translation and TTS endpoints
- Eligibility checking
- Original search/drift/recommendations endpoints
"""

import os
import logging
from typing import List, Dict, Optional, Any
from uuid import uuid4
from io import BytesIO

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Import PolicyPulse modules
from .chromadb_setup import query_documents, get_collection_info, add_documents
from .reasoning import generate_reasoning_trace
from .drift import compute_drift_timeline
from .recommendations import get_related_policies
from .embeddings import embed_text, get_sentiment
from .translation import translate_text, translate_response
from .tts import text_to_speech
from .eligibility import check_eligibility, get_next_steps
from .document_checker import process_document, check_scheme_requirements
from .performance import get_performance_stats, log_query_performance
from .language_detection import detect_language, get_language_name
from .query_processor import process_query

# Load environment variables
load_dotenv()

# Logging setup
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/policypulse.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="PolicyPulse API",
    version="2.0",
    description="Community-first policy information assistant"
)

# Rate limiting
# 200/min seemed reasonable, haven't hit this in testing yet
# might need to bump for demo day traffic
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted at /static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


# ===== Request/Response Models =====

class QueryRequest(BaseModel):
    query_text: str
    top_k: Optional[int] = 5
    language: Optional[str] = 'en'
    
    @validator('query_text')
    def validate_query(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Query too short (min 3 characters)')
        if len(v) > 500:
            raise ValueError('Query too long (max 500 characters)')  # was 1000, reduced for perf
        return v


class TranslateRequest(BaseModel):
    text: str
    target_lang: str = 'hi'
    source_lang: str = 'en'


class TTSRequest(BaseModel):
    text: str
    lang: str = 'hi'
    slow: Optional[bool] = False


class EligibilityProfile(BaseModel):
    age: int
    income: int = 0
    occupation: str = ''
    location_type: str = 'urban'
    category: str = 'general'
    land_ownership: bool = False
    has_toilet: bool = True
    willingness_manual_work: bool = False
    in_smart_city: bool = False


# ===== Root & Static Routes =====

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main landing page."""
    try:
        return FileResponse("static/index.html")
    except Exception:
        return HTMLResponse("""
            <h1>PolicyPulse API</h1>
            <p>API is running. UI files not found in static/</p>
            <p>API Documentation: <a href="/docs">/docs</a></p>
        """)


@app.get("/search.html", response_class=HTMLResponse)
async def search_page():
    """Serve search page."""
    return FileResponse("static/search.html")


@app.get("/eligibility.html", response_class=HTMLResponse)
async def eligibility_page():
    """Serve eligibility checker page."""
    return FileResponse("static/eligibility.html")


@app.get("/documents.html", response_class=HTMLResponse)
async def documents_page():
    """Serve document checker page."""
    return FileResponse("static/documents.html")


@app.get("/voice.html", response_class=HTMLResponse)
async def voice_page():
    """Serve voice assistant page."""
    return FileResponse("static/voice.html")


# ===== API Endpoints =====

@app.post("/query")
@limiter.limit("20/minute") 
async def query_policies(request: Request, query_req: QueryRequest):
    """
    Query policy documents using semantic search.
    
    Features:
    - Semantic vector search
    - 7-step reasoning trace
    - Auto-translates non-English queries for better retrieval
    """
    try:
        original_query = query_req.query_text
        
        # Step 1: Detect query language
        detected_lang, lang_confidence = detect_language(original_query)
        
        # Step 2: If not English, translate query to English for better retrieval
        search_query = original_query
        if detected_lang != 'en':
            search_query = translate_text(original_query, target_lang='en', source_lang=detected_lang)
            logger.info(f"Translated query: '{original_query[:30]}...' -> '{search_query[:30]}...'")
        
        # Step 3: Process query to extract policy and year filters
        query_info = process_query(search_query)
        
        # Check if this is a "what changed" comparison query
        is_comparison_query = any(word in search_query.lower() for word in ['change', 'changed', 'differ', 'difference', 'between', 'evolution'])
        year_start = query_info.get("year_start")
        year_end = query_info.get("year_end")
        policy_id = query_info.get("policy_id")
        
        if is_comparison_query and year_start and year_end and year_start != year_end and policy_id:
            # TEMPORAL COMPARISON: Fetch data from both years and compare
            logger.info(f"Temporal comparison query: {policy_id} {year_start} vs {year_end}")
            
            # Get data from start year (years stored as strings in DB)
            start_results = query_documents(
                query_text=f"{policy_id} {year_start}",
                n_results=3,
                where={"$and": [{"policy_id": policy_id}, {"year": str(year_start)}]}
            )
            
            # Get data from end year
            end_results = query_documents(
                query_text=f"{policy_id} {year_end}",
                n_results=3,
                where={"$and": [{"policy_id": policy_id}, {"year": str(year_end)}]}
            )
            
            # Synthesize comparison answer
            start_docs = start_results.get('documents', [[]])[0]
            end_docs = end_results.get('documents', [[]])[0]
            
            comparison_answer = f"**{policy_id} Changes ({year_start} → {year_end}):**\n\n"
            
            if start_docs:
                comparison_answer += f"**{year_start}:** {start_docs[0][:800]}\n\n"
            else:
                comparison_answer += f"**{year_start}:** No specific data available for this year.\n\n"
            
            if end_docs:
                comparison_answer += f"**{year_end}:** {end_docs[0][:800]}"
            else:
                comparison_answer += f"**{year_end}:** No specific data available for this year."
            
            # Build reasoning trace manually for comparison
            reasoning = {
                "query": search_query,
                "final_answer": comparison_answer,
                "confidence_score": 0.7 if (start_docs or end_docs) else 0.3,
                "retrieved_points": [],
                "comparison_mode": True,
                "years_compared": [year_start, year_end]
            }
        else:
            # Standard query flow
            results = query_documents(
                query_text=search_query,
                n_results=query_req.top_k,
                where=query_info.get("filter")
            )
            
            # Fallback: if no results with year filter, retry with just policy filter
            ids = results.get('ids', [[]])[0]
            if not ids and query_info.get("year_start"):
                logger.info("No results with year filter, retrying with policy only")
                policy_only_filter = {"policy_id": query_info["policy_id"]} if query_info.get("policy_id") else None
                results = query_documents(
                    query_text=search_query,
                    n_results=query_req.top_k,
                    where=policy_only_filter
                )
            
            # Generate reasoning trace
            reasoning = generate_reasoning_trace(
                query=search_query,
                retrieved_results=results
            )
        
        # Add query understanding info
        reasoning["original_query"] = original_query
        reasoning["detected_language"] = detected_lang
        reasoning["language_confidence"] = lang_confidence
        if query_info.get("policy_id"):
            reasoning["detected_policy"] = query_info["policy_id"]
        if query_info.get("year_start"):
            reasoning["year_filter"] = f"{query_info['year_start']}-{query_info['year_end']}"
        
        # Add confidence label
        confidence = reasoning.get("confidence_score", 0)
        if confidence >= 0.7:
            reasoning["confidence_label"] = "High"
        elif confidence >= 0.45:
            reasoning["confidence_label"] = "Medium"
        else:
            reasoning["confidence_label"] = "Low"
        
        # Step 6: Translate response back to user's language
        if detected_lang != 'en':
            reasoning = translate_response(reasoning, detected_lang)
        
        # Log performance
        if 'comparison_mode' in reasoning and reasoning['comparison_mode']:
            log_query_performance(query_req.query_text, len(reasoning.get('years_compared', [])))
        else:
            log_query_performance(query_req.query_text, len(results.get('ids', [[]])[0]))
        
        return reasoning
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-language")
@limiter.limit("30/minute")
async def detect_query_language(request: Request, text: str = ""):
    """
    Auto-detect the language of input text.
    
    Returns language code, confidence score, and display name.
    Supports 10 Indian languages + English.
    """
    if not text:
        # Try to get from request body
        body = await request.body()
        text = body.decode('utf-8') if body else ""
    
    if not text:
        return {"language": "en", "confidence": 0.0, "name": "English"}
    
    lang_code, confidence = detect_language(text)
    
    return {
        "language": lang_code,
        "confidence": round(confidence, 3),
        "name": get_language_name(lang_code)
    }


@app.get("/drift/{policy_id}")
@limiter.limit("10/minute")
async def get_drift(request: Request, policy_id: str):
    """Get drift analysis for a policy."""
    try:
        drift_data = compute_drift_timeline(policy_id)
        return drift_data
    except Exception as e:
        logger.error(f"Drift analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/{policy_id}")
@limiter.limit("15/minute")
async def get_policy_recommendations(request: Request, policy_id: str, count: int = 3):
    """Get related policy recommendations."""
    try:
        recommendations = get_related_policies(policy_id, top_k=count)
        return {"policy_id": policy_id, "recommendations": recommendations}
    except Exception as e:
        logger.error(f"Recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/translate")
@limiter.limit("30/minute")
async def translate_endpoint(request: Request, translate_req: TranslateRequest):
    """
    Translate text to target language.
    
    Uses Google Translate API if configured, otherwise googletrans (free).
    """
    try:
        translated = translate_text(
            translate_req.text,
            target_lang=translate_req.target_lang,
            source_lang=translate_req.source_lang
        )
        return {
            "original": translate_req.text,
            "translated": translated,
            "target_lang": translate_req.target_lang
        }
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tts")
@limiter.limit("20/minute")
async def text_to_speech_endpoint(request: Request, tts_req: TTSRequest):
    """
    Convert text to speech audio.
    
    Returns MP3 audio file.
    """
    try:
        audio_bytes = text_to_speech(
            tts_req.text,
            lang=tts_req.lang,
            slow=tts_req.slow
        )
        
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="TTS generation failed")
        
        return StreamingResponse(
            BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-audio")
@limiter.limit("10/minute")
async def process_audio_endpoint(request: Request, file: UploadFile = File(...)):
    """
    Process audio file and transcribe to text using SpeechRecognition.
    
    Accepts audio files (webm, wav, mp3) and returns transcription.
    """
    try:
        import speech_recognition as sr
        import tempfile
        import os
        
        # Save uploaded file temporarily
        content = await file.read()
        suffix = ".webm" if "webm" in file.filename else ".wav"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Convert to WAV if needed (webm needs conversion)
            if suffix == ".webm":
                try:
                    import av
                    wav_path = tmp_path + ".wav"
                    
                    container = av.open(tmp_path)
                    audio_stream = container.streams.audio[0]
                    
                    output = av.open(wav_path, 'w')
                    output_stream = output.add_stream('pcm_s16le', rate=16000)
                    
                    for frame in container.decode(audio_stream):
                        for packet in output_stream.encode(frame):
                            output.mux(packet)
                    
                    for packet in output_stream.encode():
                        output.mux(packet)
                    
                    output.close()
                    container.close()
                    
                    audio_path = wav_path
                except Exception as conv_err:
                    logger.warning(f"Audio conversion failed: {conv_err}, trying direct recognition")
                    audio_path = tmp_path
            else:
                audio_path = tmp_path
            
            # Recognize speech
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            
            # Try Google Speech Recognition
            try:
                transcription = recognizer.recognize_google(audio, language="hi-IN")
            except sr.UnknownValueError:
                # Try English if Hindi fails
                try:
                    transcription = recognizer.recognize_google(audio, language="en-IN")
                except:
                    transcription = ""
            
            # Clean up temp files
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if suffix == ".webm" and os.path.exists(audio_path) and audio_path != tmp_path:
                os.unlink(audio_path)
            
            if transcription:
                return {"transcription": transcription, "success": True}
            else:
                return {"transcription": "", "success": False, "error": "Could not understand audio"}
                
        except Exception as e:
            logger.error(f"Speech recognition failed: {e}")
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return {"transcription": "", "success": False, "error": str(e)}
            
    except ImportError:
        logger.warning("speech_recognition not installed, returning mock response")
        return {
            "transcription": "Voice input not available - SpeechRecognition not installed",
            "success": False,
            "error": "speech_recognition library not installed"
        }
    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/eligibility/check")
@limiter.limit("30/minute")
async def check_user_eligibility(request: Request, profile: EligibilityProfile):
    """
    Check which schemes a user is eligible for.
    
    Returns list of eligible schemes with application details.
    """
    try:
        eligible_schemes = check_eligibility(profile.dict())
        return eligible_schemes
    except Exception as e:
        logger.error(f"Eligibility check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/eligibility/steps/{policy_id}")
@limiter.limit("20/minute")
async def get_application_steps(request: Request, policy_id: str):
    """Get application steps for a specific policy."""
    try:
        steps = get_next_steps(policy_id)
        return steps
    except Exception as e:
        logger.error(f"Failed to get steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/document/upload")
@limiter.limit("10/minute")
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Upload and process a document image (Aadhaar, income cert, land records, etc.).
    
    Returns:
        Extracted text, document type, fields, and validation status
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are supported")
        
        # Read file bytes
        image_bytes = await file.read()
        
        # Validate file size (max 10MB)
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Process document
        result = process_document(image_bytes)
        
        if not result['success']:
            return {
                "success": False,
                "error": result.get('error', 'Processing failed')
            }
        
        logger.info(f"Processed {result['document_type']} document")
        
        return {
            "success": True,
            "document_type": result['document_type'],
            "extracted_fields": result['extracted_fields'],
            "validation": result['validation'],
            "ocr_preview": result['ocr_text']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")


@app.post("/document/check-requirements")
@limiter.limit("20/minute")
async def check_document_requirements(request: Request, data: Dict[str, Any]):
    """
    Check which scheme requirements are met by user's documents.
    
    Request body:
        {
            "user_documents": ["aadhaar", "income_certificate"],
            "eligible_schemes": ["NREGA", "PM-KISAN"]
        }
    """
    try:
        user_documents = data.get('user_documents', [])
        eligible_schemes = data.get('eligible_schemes', [])
        
        requirements = check_scheme_requirements(user_documents, eligible_schemes)
        
        return {
            "success": True,
            "requirements": requirements
        }
        
    except Exception as e:
        logger.error(f"Requirement check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/stats")
async def get_stats(request: Request):
    """Get system statistics."""
    try:
        db_info = get_collection_info()
        perf_stats = get_performance_stats()
        
        return {
            "database": db_info,
            "performance": perf_stats,
            "version": "2.0",
            "features": {
                "translation": True,
                "tts": True,
                "eligibility": True,
                "voice": True
            }
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "PolicyPulse API",
        "version": "2.0"
    }


# Startup message
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("PolicyPulse API v2.0 Started")
    logger.info("Community-First Policy Information Platform")
    logger.info("=" * 50)
    logger.info("Features:")
    logger.info("  - Semantic Policy Search")
    logger.info("  - Multilingual Translation")
    logger.info("  - Text-to-Speech (10+ languages)")
    logger.info("  - Eligibility Checking")
    logger.info("  - Voice Interface")
    logger.info("  - Drift Analysis")
    logger.info("=" * 50)
