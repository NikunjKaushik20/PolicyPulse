"""
PolicyPulse REST API - Policy analysis and recommendation service.

FastAPI-based service providing:
- Vector search and reasoning across policy documents
- Drift detection for policy evolution
- Related policy recommendations
- Adaptive memory management with decay and reinforcement
- Document ingestion and indexing
"""

import os
import logging
import traceback
import re
from typing import List, Dict, Optional, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from pydantic import BaseModel, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from qdrant_client.models import PointStruct

from .drift import compute_drift_timeline, find_max_drift
from .reasoning import generate_reasoning_trace
from .recommendations import get_related_policies
from .memory import apply_time_decay, consolidate_memories, get_memory_health
from .qdrant_setup import get_collection_info, get_client, COLLECTION_NAME
from .embeddings import embed_text, get_sentiment, embed_image
from .performance import get_performance_stats, log_query_performance
import pytesseract

# ===== Logging Configuration =====
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

# ===== Application Configuration =====
app = FastAPI(
    title="PolicyPulse API",
    version="1.0",
    description="AI-Powered Policy Evolution and Accountability Analysis"
)

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ===== Request Validation Constants =====
POLICY_ID_MAX_LENGTH = 100
QUESTION_MIN_LENGTH = 3
QUESTION_MAX_LENGTH = 500
TOP_K_MIN = 1
TOP_K_MAX = 50
YEAR_MIN = 1900
YEAR_MAX = 2100
CONTENT_MIN_LENGTH = 50
CONTENT_MAX_BYTES = 10_000_000
SIMILARITY_THRESHOLD_MIN = 0.5
SIMILARITY_THRESHOLD_MAX = 1.0

# Ingest configuration
MAX_CHUNKS_FROM_UPLOAD = 20
MIN_CHUNK_LENGTH = 50
MAX_CHUNK_LENGTH = 500
SENTENCE_SPLIT_PATTERN = r'(?<=[.!?])\s+'

# Rate limit settings per endpoint
RATE_LIMIT_QUERY = "20/minute"
RATE_LIMIT_DRIFT = "10/minute"
RATE_LIMIT_RECOMMENDATIONS = "15/minute"
RATE_LIMIT_DECAY = "10/minute"
RATE_LIMIT_INGEST = "5/minute"
RATE_LIMIT_CONSOLIDATE = "5/minute"



# ===== Request Models (Centralized Validators) =====
class QueryRequest(BaseModel):
    policy_id: str
    question: str
    top_k: Optional[int] = 5

    @validator('policy_id')
    def validate_policy_id(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('policy_id cannot be empty')
        if len(v) > POLICY_ID_MAX_LENGTH:
            raise ValueError(f'policy_id too long (max {POLICY_ID_MAX_LENGTH})')
        return v

    @validator('question')
    def validate_question(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('question cannot be empty')
        if len(v) < QUESTION_MIN_LENGTH:
            raise ValueError(f'question too short (min {QUESTION_MIN_LENGTH})')
        if len(v) > QUESTION_MAX_LENGTH:
            raise ValueError(f'question too long (max {QUESTION_MAX_LENGTH})')
        return v

    @validator('top_k')
    def validate_top_k(cls, v):
        if v < TOP_K_MIN or v > TOP_K_MAX:
            raise ValueError(f'top_k must be {TOP_K_MIN}-{TOP_K_MAX}')
        return v

class DriftRequest(BaseModel):
    policy_id: str
    modality: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None

    @validator('policy_id')
    def validate_policy_id(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('policy_id cannot be empty')
        return v

    @validator('modality')
    def validate_modality(cls, v):
        v = v.lower()
        if v == "text":
            return "temporal"
        if v not in ['budget', 'news', 'temporal']:
            raise ValueError('modality must be: text, budget, news, or temporal')
        return v

class RecommendationsRequest(BaseModel):
    policy_id: str
    year: Optional[int] = None
    top_k: Optional[int] = 5

    @validator('policy_id')
    def validate_policy_id(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('policy_id cannot be empty')
        return v

    @validator('year')
    def validate_year(cls, v):
        if v and (v < YEAR_MIN or v > YEAR_MAX):
            raise ValueError(f'year must be {YEAR_MIN}-{YEAR_MAX}')
        return v

    @validator('top_k')
    def validate_top_k(cls, v):
        if v < TOP_K_MIN or v > TOP_K_MAX:
            raise ValueError(f'top_k must be {TOP_K_MIN}-{TOP_K_MAX}')
        return v


# New: Image ingestion endpoint
from fastapi.responses import JSONResponse
import shutil
import os

# Existing IngestRequest for text
class IngestRequest(BaseModel):
    policy_id: str
    content: Optional[str] = None
    year: Optional[str] = None
    modality: Optional[str] = "temporal"
    filename: Optional[str] = "uploaded_doc.txt"

    @validator('policy_id')
    def validate_policy_id(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('policy_id cannot be empty')
        return v

    @validator('modality')
    def validate_modality(cls, v):
        if v not in ['budget', 'news', 'temporal', 'image']:
            raise ValueError('modality must be: budget, news, temporal, or image')
        return v

    @validator('content')
    def validate_content(cls, v, values):
        if values.get('modality') == 'image':
            return v
        if v is None or not v.strip():
            raise ValueError('content cannot be empty')
        if len(v) < CONTENT_MIN_LENGTH:
            raise ValueError(f'content too short (min {CONTENT_MIN_LENGTH})')
        if len(v) > CONTENT_MAX_BYTES:
            raise ValueError(f'content too large (max {CONTENT_MAX_BYTES} bytes)')
        return v

# ===== Image Upload Endpoint =====
from .embeddings import embed_audio, embed_video
import shutil
import uuid
# ===== Audio Upload Endpoint =====
@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload an audio file, embed as vector, and ingest with evidence trace.
    """
    try:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Embed audio (CLAP)
        audio_vec = embed_audio(file_path, model_type="clap")
        # Duration/timestamp
        import librosa
        y, sr = librosa.load(file_path, sr=48000)
        duration = librosa.get_duration(y=y, sr=sr)
        timestamp = duration / 2

        # TODO: auto-detect policy/year from filename or metadata
        payload = {
            "policy_id": "NREGA",
            "year": 2023,
            "modality": "audio",
            "audio_vector": audio_vec,
            "audio_timestamp": timestamp,
            "evidence_uri": file_path
        }
        client = get_client()
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=audio_vec,
            payload=payload
        )
        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "audio_embedding": audio_vec,
            "audio_timestamp": timestamp
        })
    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio upload failed: {e}")

# ===== Video Upload Endpoint =====
@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file, embed as vector, and ingest with evidence trace.
    """
    try:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Embed video (VideoCLIP)
        video_vec = embed_video(file_path)
        # Frame (middle) using ffmpeg-python
        import ffmpeg
        probe = ffmpeg.probe(file_path)
        video_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']
        if not video_streams:
            raise Exception('No video stream found')
        video_stream = video_streams[0]
        fps = eval(video_stream['r_frame_rate']) if 'r_frame_rate' in video_stream else 25
        duration = float(video_stream['duration']) if 'duration' in video_stream else 0
        frame_num = int(fps * (duration / 2)) if duration > 0 else 0

        # TODO: auto-detect policy/year from filename or metadata
        payload = {
            "policy_id": "NREGA",
            "year": 2023,
            "modality": "video",
            "video_vector": video_vec,
            "video_frame": frame_num,
            "evidence_uri": file_path
        }
        client = get_client()
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=video_vec,
            payload=payload
        )
        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "video_embedding": video_vec,
            "video_frame": frame_num
        })
    except Exception as e:
        logger.error(f"Video upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Video upload failed: {e}")

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image file, extract text, infer policy and year, and ingest as a vector embedding.
    """
    try:
        # Save uploaded file temporarily
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # OCR: Extract text from image
        from PIL import Image
        image = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(image)

        # Try to infer policy and year from extracted text
        # Policy: match against known policy names
        known_policies = [
            "NREGA", "RTI", "NEP", "PM-KISAN", "SWACHH-BHARAT",
            "DIGITAL-INDIA", "AYUSHMAN-BHARAT", "MAKE-IN-INDIA",
            "SKILL-INDIA", "SMART-CITIES"
        ]
        policy_id = None
        for policy in known_policies:
            if policy.replace("-", " ").lower() in extracted_text.lower().replace("-", " "):
                policy_id = policy
                break

        # Year: look for 4-digit year
        import re
        year_match = re.search(r"(20\d{2}|19\d{2})", extracted_text)
        year = year_match.group(1) if year_match else None

        # Embed image
        vector = embed_image(file_path)

        # Prepare payload
        payload = {
            "policy_id": policy_id or "UNKNOWN",
            "content": file.filename,
            "timestamp": f"{year}-01-01T00:00:00Z" if year else None,
            "year": year,
            "modality": "image",
            "filename": file.filename,
            "ocr_text": extracted_text,
            "decay_weight": 1.0,
            "access_count": 0
        }

        # Store in Qdrant
        client = get_client()
        point = PointStruct(
            id=str(uuid4()),
            vector=vector,
            payload=payload
        )
        client.upsert(collection_name=COLLECTION_NAME, points=[point])

        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "extracted_text": extracted_text,
            "policy_id": policy_id or "UNKNOWN",
            "year": year
        })
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image upload failed: {e}")


# ===== Health and Status Endpoints =====
@app.get("/")
def root() -> Dict[str, str]:
    """Root endpoint providing service information."""
    return {
        "service": "PolicyPulse API",
        "version": "1.0",
        "status": "operational"
    }


@app.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Dict with service status, Qdrant connectivity, and collection info.
    """
    try:
        client = get_client()
        collections = client.get_collections()
        return {
            "status": "healthy",
            "qdrant": "connected",
            "api": "operational",
            "collections": len(collections.collections)
        }
    except Exception as error:
        logger.error(f"Health check failed: {error}")
        return {
            "status": "degraded",
            "qdrant": "error",
            "api": "operational",
            "error": str(error)
        }


# ===== Core Query Endpoints =====
@app.post("/query")
@limiter.limit(RATE_LIMIT_QUERY)
def query_policy(request: Request, req: QueryRequest) -> Dict[str, Any]:
    # Semantic search with multi-step reasoning
    try:
        trace = generate_reasoning_trace(
            query=req.question,
            policy_id=req.policy_id,
            top_k=req.top_k
        )
        return trace
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(error)}")


def _get_available_years(policy_id: str, modality: str) -> List[int]:
    """
    Get sorted list of available years for a policy and modality.
    
    Args:
        policy_id: Policy identifier.
        modality: Data modality (budget/news/temporal).
        
    Returns:
        List of years with data.
        
    Raises:
        ValueError: If no data found.
    """
    client = get_client()
    
    # Retrieve all points (with pagination if needed)
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="policy_id", match=MatchValue(value=policy_id)),
                FieldCondition(key="modality", match=MatchValue(value=modality))
            ]
        ),
        limit=10_000,
        with_payload=True,
        with_vectors=False
    )

    years = set()
    for point in points:
        year = point.payload.get("year")
        if year is not None:
            try:
                years.add(int(year))
            except (ValueError, TypeError):
                continue

    if not years:
        raise ValueError(
            f"No year data found for policy '{policy_id}' with modality '{modality}'"
        )

    return sorted(years)


@app.post("/drift")
@limiter.limit(RATE_LIMIT_DRIFT)
def get_drift(request: Request, req: DriftRequest) -> Dict[str, Any]:
    # Analyze semantic drift in a policy over time
    try:
        if req.start_year is None or req.end_year is None:
            try:
                available_years = _get_available_years(req.policy_id, req.modality)
                req.start_year = available_years[0]
                req.end_year = available_years[-1]
            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error))
        if req.start_year >= req.end_year:
            raise HTTPException(status_code=400, detail="start_year must be less than end_year")
        timeline = compute_drift_timeline(
            policy_id=req.policy_id,
            modality=req.modality
        )
        if not timeline:
            return {
                "error": "Insufficient data for drift analysis",
                "policy_id": req.policy_id,
                "suggestion": "Need at least 2 years with sufficient samples"
            }
        max_drift_period = find_max_drift(req.policy_id, req.modality)
        return {
            "policy_id": req.policy_id,
            "timeline": timeline,
            "max_drift": max_drift_period,
            "total_periods": len(timeline),
            "start_year": req.start_year,
            "end_year": req.end_year
        }
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(error)}")


@app.post("/recommendations")
@limiter.limit(RATE_LIMIT_RECOMMENDATIONS)
def get_recommendations(request: Request, req: RecommendationsRequest) -> Dict[str, Any]:
    # Get related policies based on semantic similarity
    try:
        related_policies = get_related_policies(
            policy_id=req.policy_id,
            year=req.year,
            top_k=req.top_k
        )
        return {
            "policy_id": req.policy_id,
            "recommendations": related_policies,
            "count": len(related_policies)
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(error)}")


# ===== Collection Statistics =====
@app.get("/stats")
def get_stats() -> Dict[str, Any]:
    """
    Get collection statistics and policy breakdown.
    
    Returns:
        Dict with collection metadata and policy counts.
        
    Raises:
        HTTPException: 500 if stats retrieval fails.
    """
    try:
        info = get_collection_info()
        return info
    except Exception as error:
        logger.error(f"Stats retrieval error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


# ===== Memory Management Endpoints =====
@app.post("/memory/decay")
@limiter.limit(RATE_LIMIT_DECAY)
def trigger_decay(request: Request, policy_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Apply time decay to policy data based on age.
    
    Older data naturally decreases in relevance weight.
    
    Args:
        request: FastAPI request object.
        policy_id: Optional policy to decay (all if omitted).
        
    Returns:
        Dict with number of points updated.
        
    Raises:
        HTTPException: 400 for empty policy_id, 500 for errors.
    """
    try:
        if policy_id and len(policy_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="policy_id cannot be empty if provided")
        
        target_policy = policy_id.strip() if policy_id else None
        logger.info(f"Applying time decay: policy={target_policy or 'all'}")
        
        updated_count = apply_time_decay(target_policy)
        logger.info(f"Time decay applied to {updated_count} points")
        
        return {
            "policy_id": target_policy,
            "points_updated": updated_count
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Decay error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/memory/consolidate")
@limiter.limit(RATE_LIMIT_CONSOLIDATE)
def consolidate_memory(
    request: Request,
    policy_id: str,
    year: str,
    threshold: float = 0.95
) -> Dict[str, Any]:
    # Merge similar memories to reduce redundancy
    try:
        if not policy_id or not year:
            raise HTTPException(status_code=400, detail="policy_id and year required")
        if threshold < SIMILARITY_THRESHOLD_MIN or threshold > SIMILARITY_THRESHOLD_MAX:
            raise HTTPException(status_code=400, detail=f"threshold must be {SIMILARITY_THRESHOLD_MIN}-{SIMILARITY_THRESHOLD_MAX}")
        consolidated_count = consolidate_memories(policy_id.strip(), year.strip(), threshold)
        return {
            "policy_id": policy_id,
            "year": year,
            "memories_consolidated": consolidated_count,
            "threshold": threshold
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/memory/health")
def memory_health(policy_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get memory health statistics.
    
    Args:
        policy_id: Optional policy to analyze (all if omitted).
        
    Returns:
        Dict with memory health metrics.
        
    Raises:
        HTTPException: 400 for empty policy_id, 500 for errors.
    """
    try:
        if policy_id and len(policy_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="policy_id cannot be empty if provided")
        
        target_policy = policy_id.strip() if policy_id else None
        health_stats = get_memory_health(target_policy)
        return health_stats
    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Memory health error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(error))


# ===== Document Ingestion =====
@app.post("/ingest-document")
@limiter.limit(RATE_LIMIT_INGEST)
def ingest_document(request: Request, req: IngestRequest) -> Dict[str, Any]:
    # Ingest and index a new policy document
    try:
        client = get_client()
        paragraphs = [
            p.strip() for p in req.content.split('\n\n')
            if p.strip() and len(p.strip()) > MIN_CHUNK_LENGTH
        ]
        if len(paragraphs) < 2:
            sentences = re.split(SENTENCE_SPLIT_PATTERN, req.content)
            chunks = []
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) < MAX_CHUNK_LENGTH:
                    current_chunk += sentence + " "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
            if current_chunk:
                chunks.append(current_chunk.strip())
        else:
            chunks = paragraphs
        if not chunks:
            raise HTTPException(status_code=400, detail="No valid chunks extracted from document")
        points_to_upsert = []
        chunk_previews = []
        for chunk in chunks[:MAX_CHUNKS_FROM_UPLOAD]:
            if len(chunk) < MIN_CHUNK_LENGTH:
                continue
            embedding_vector = embed_text(chunk)
            sentiment_label = get_sentiment(chunk)
            payload = {
                "policy_id": req.policy_id,
                "year": req.year if req.year else "2026",
                "modality": req.modality,
                "content": chunk,
                "sentiment": sentiment_label,
                "source": req.filename,
                "decay_weight": 1.0,
                "access_count": 0
            }
            point = PointStruct(
                id=str(uuid4()),
                vector=embedding_vector,
                payload=payload
            )
            points_to_upsert.append(point)
            chunk_previews.append(chunk[:100])
        if not points_to_upsert:
            raise HTTPException(status_code=400, detail="No valid chunks met minimum length requirement")
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points_to_upsert
        )
        return {
            "status": "success",
            "policy_id": req.policy_id,
            "chunks_added": len(points_to_upsert),
            "year": req.year or "2026",
            "modality": req.modality,
            "chunks_preview": chunk_previews[:3]
        }
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(error)}")

# request models
class QueryRequest(BaseModel):
    policy_id: str
    question: str
    top_k: Optional[int] = 5
    
    @validator('policy_id')
    def validate_policy_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('policy_id cannot be empty')
        if len(v) > 100:
            raise ValueError('policy_id too long (max 100)')
        return v.strip()
    
    @validator('question')
    def validate_question(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('question cannot be empty')
        if len(v) < 3:
            raise ValueError('question too short (min 3)')
        if len(v) > 500:
            raise ValueError('question too long (max 500)')
        return v.strip()
    
    @validator('top_k')
    def validate_top_k(cls, v):
        if v < 1 or v > 50:
            raise ValueError('top_k must be 1-50')
        return v

class DriftRequest(BaseModel):
    policy_id: str
    modality: str
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    
    @validator('policy_id')
    def validate_policy_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('policy_id cannot be empty')
        return v.strip()
    
    @validator('modality')
    def validate_modality(cls, v):
        v = v.lower()
        if v == "text":
            return "temporal"  
        if v not in ['budget', 'news', 'temporal']:
            raise ValueError('modality must be: text, budget, news, or temporal')
        return v


class RecommendationsRequest(BaseModel):
    policy_id: str
    year: Optional[int] = None
    top_k: Optional[int] = 5
    
    @validator('policy_id')
    def validate_policy_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('policy_id cannot be empty')
        return v.strip()
    
    @validator('year')
    def validate_year(cls, v):
        if v and (v < 1900 or v > 2100):
            raise ValueError('year must be 1900-2100')
        return v
    
    @validator('top_k')
    def validate_top_k(cls, v):
        if v < 1 or v > 50:
            raise ValueError('top_k must be 1-50')
        return v

class IngestRequest(BaseModel):
    policy_id: str
    content: str
    year: Optional[str] = None
    modality: Optional[str] = "temporal"
    filename: Optional[str] = "uploaded_doc.txt"
    
    @validator('policy_id')
    def validate_policy_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('policy_id cannot be empty')
        return v.strip()
    
    @validator('content')
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('content cannot be empty')
        if len(v) < 50:
            raise ValueError('content too short (min 50)')
        if len(v) > 10_000_000:
            raise ValueError('content too large (max 10MB)')
        return v.strip()
    
    @validator('modality')
    def validate_modality(cls, v):
        if v not in ['budget', 'news', 'temporal']:
            raise ValueError('modality must be: budget, news, or temporal')
        return v

@app.get("/")
def root():
    return {
        "service": "PolicyPulse API",
        "version": "1.0",
        "status": "operational"
    }

@app.get("/health")
def health_check():
    try:
        client = get_client()
        colls = client.get_collections()
        return {
            "status": "healthy",
            "qdrant": "connected",
            "api": "operational",
            "collections": len(colls.collections)
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "degraded",
            "qdrant": "error",
            "api": "operational",
            "error": str(e)
        }

@app.post("/query")
@limiter.limit("20/minute")
def query_policy(request: Request, req: QueryRequest):
    try:
        logger.info(f"Query: policy={req.policy_id}, q={req.question[:40]}")
        
        trace = generate_reasoning_trace(
            query=req.question,
            policy_id=req.policy_id,
            top_k=req.top_k
        )
        
        logger.info(f"Query done: {len(trace.get('retrieved_points', []))} points")
        return trace
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Query error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


def get_available_years(policy_id: str, modality: str):
    """Helper function to get available years for a policy and modality"""
    client = get_client()
    
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter={
            "must": [
                {"key": "policy_id", "match": {"value": policy_id}},
                {"key": "modality", "match": {"value": modality}}
            ]
        },
        limit=10_000,
        with_payload=True,
        with_vectors=False,
    )

    years = set()
    for p in points:
        year = p.payload.get("year")
        if year is not None:
            # Handle both string and int years
            try:
                years.add(int(year))
            except (ValueError, TypeError):
                continue

    if not years:
        raise ValueError(
            f"No year metadata found for policy '{policy_id}' with modality '{modality}'"
        )

    return sorted(years)


@app.post("/drift")
@limiter.limit("10/minute")
def get_drift(request: Request, req: DriftRequest):
    try:
        logger.info(f"Drift: policy={req.policy_id}, mod={req.modality}")
        
        # Auto-detect year range if not provided
        if req.start_year is None or req.end_year is None:
            try:
                years = get_available_years(req.policy_id, req.modality)
                req.start_year = years[0]
                req.end_year = years[-1]
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
        
        if req.start_year >= req.end_year:
            raise HTTPException(
                status_code=400,
                detail="start_year must be less than end_year",
            )
        
        timeline = compute_drift_timeline(
            policy_id=req.policy_id,
            modality=req.modality
        )
        
        if timeline is None or len(timeline) == 0:
            return {
                "error": "Insufficient data",
                "policy_id": req.policy_id,
                "suggestion": "Need at least 2 years with 3+ samples each"
            }
        
        max_drift = find_max_drift(req.policy_id, req.modality)
        
        logger.info(f"Drift done: {len(timeline)} periods")
        return {
            "policy_id": req.policy_id,
            "timeline": timeline,
            "max_drift": max_drift,
            "total_periods": len(timeline),
            "start_year": req.start_year,
            "end_year": req.end_year
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Drift error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/recommendations")
@limiter.limit("15/minute")
def get_recommendations_endpoint(request: Request, req: RecommendationsRequest):
    try:
        logger.info(f"Recommendations: policy={req.policy_id}")
        
        results = get_related_policies(
            policy_id=req.policy_id,
            year=req.year,
            top_k=req.top_k
        )
        
        logger.info(f"Recommendations done: {len(results)} found")
        return {
            "policy_id": req.policy_id,
            "recommendations": results,
            "count": len(results)
        }
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Recommendations error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/stats")
def get_stats():
    try:
        info = get_collection_info()
        return info
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/decay")
@limiter.limit("10/minute")
def trigger_decay(request: Request, policy_id: str):
    try:
        if not policy_id or len(policy_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="policy_id empty")
        
        logger.info(f"Decay: policy={policy_id}")
        cnt = apply_time_decay(policy_id.strip())
        logger.info(f"Decay done: {cnt} points")
        
        return {"policy_id": policy_id, "points_updated": cnt}
    except Exception as e:
        logger.error(f"Decay error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest-document")
@limiter.limit("5/minute")
def ingest_document(request: Request, req: IngestRequest):
    try:
        logger.info(f"Ingest: policy={req.policy_id}, size={len(req.content)}")
        
        client = get_client()
        
        # try to chunk by paragraphs first
        paras = [p.strip() for p in req.content.split('\n\n') if p.strip() and len(p.strip()) > 50]
        
        if len(paras) < 2:
            # fallback - split by sentences
            sents = re.split(r'(?<=[.!?])\s+', req.content)
            chunks = []
            curr = ""
            
            for s in sents:
                if len(curr) + len(s) < 500:
                    curr += s + " "
                else:
                    if curr:
                        chunks.append(curr.strip())
                    curr = s + " "
            
            if curr:
                chunks.append(curr.strip())
        else:
            chunks = paras
        
        if len(chunks) == 0:
            raise HTTPException(status_code=400, detail="No valid chunks extracted")
        
        # create vector points
        points = []
        preview = []
        
        for i, chunk in enumerate(chunks[:20]):  # limit to 20 chunks
            if len(chunk) < 50:
                continue
            
            vec = embed_text(chunk)
            sent = get_sentiment(chunk)
            
            payload = {
                "policy_id": req.policy_id,
                "year": req.year if req.year else "2026",
                "modality": req.modality,
                "content": chunk,
                "sentiment": sent,
                "source": req.filename,
                "decay_weight": 1.0,
                "access_count": 0,
                "last_accessed": None
            }
            
            pt = PointStruct(
                id=str(uuid4()),
                vector=vec,
                payload=payload
            )
            
            points.append(pt)
            preview.append(chunk[:100])
        
        if len(points) == 0:
            raise HTTPException(status_code=400, detail="No valid chunks (all too short)")
        
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        logger.info(f"Ingest done: {len(points)} chunks")
        
        return {
            "status": "success",
            "policy_id": req.policy_id,
            "chunks_added": len(points),
            "year": req.year,
            "modality": req.modality,
            "chunks_preview": preview[:3]
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ingest error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/memory/consolidate")
@limiter.limit("5/minute")
def consolidate_endpoint(request: Request, policy_id: str, year: str, threshold: float = 0.95):
    try:
        if not policy_id or len(policy_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="policy_id empty")
        if not year or len(year.strip()) == 0:
            raise HTTPException(status_code=400, detail="year empty")
        if threshold < 0.5 or threshold > 1.0:
            raise HTTPException(status_code=400, detail="threshold must be 0.5-1.0")
        
        logger.info(f"Consolidate: policy={policy_id}, year={year}")
        cnt = consolidate_memories(policy_id.strip(), year.strip(), threshold)
        logger.info(f"Consolidate done: {cnt} merged")
        
        return {
            "policy_id": policy_id,
            "year": year,
            "memories_consolidated": cnt,
            "threshold": threshold
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consolidate error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/health")
def memory_health_endpoint(policy_id: str = None):
    try:
        if policy_id and len(policy_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="policy_id empty")
        
        health = get_memory_health(policy_id.strip() if policy_id else None)
        return health
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== Performance Monitoring Endpoint (NEW) =====
@app.get("/performance")
def get_performance() -> Dict[str, Any]:
    """
    Get real-time performance statistics.
    
    Returns:
        Dict with query latencies, throughput, and uptime metrics.
    """
    try:
        stats = get_performance_stats()
        return stats
    except Exception as e:
        logger.error(f"Performance endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
