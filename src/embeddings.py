"""
Text embedding and sentiment analysis module.

This module provides utilities for converting text to vector embeddings
and analyzing sentiment using pre-trained transformer models.
"""


from typing import List, Union
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import logging
from PIL import Image
import numpy as np
from .config import EMBEDDING_MODEL, SENTIMENT_MODEL, DEVICE

logger = logging.getLogger(__name__)

import librosa
import soundfile as sf
import fastembed
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import torch.nn.functional as F

# Model cache for lazy loading
_embedding_model: SentenceTransformer = None
_clip_model: SentenceTransformer = None
_sentiment_tokenizer: AutoTokenizer = None
_sentiment_model: AutoModelForSequenceClassification = None
_clap_model = None
_wav2vec2_processor = None
_wav2vec2_model = None
_videoclip_model = None

# --- AUDIO EMBEDDING (CLAP/Wav2Vec2) ---
def embed_audio(audio_path: str, model_type: str = "clap") -> list:
    """
    Embed audio file as vector using CLAP or Wav2Vec2 (local, no API).
    Args:
        audio_path: Path to .wav file
        model_type: 'clap' or 'wav2vec2'
    Returns:
        List[float]: Audio embedding
    """
    if model_type == "clap":
        global _clap_model
        if _clap_model is None:
            from transformers import ClapModel, ClapProcessor
            _clap_model = ClapModel.from_pretrained("laion/clap-htsat-unfused")
            _clap_processor = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
        audio, sr = librosa.load(audio_path, sr=48000)
        inputs = _clap_processor(audios=audio, sampling_rate=48000, return_tensors="pt")
        with torch.no_grad():
            emb = _clap_model.get_audio_features(**inputs)
        return emb[0].cpu().numpy().tolist()
    elif model_type == "wav2vec2":
        global _wav2vec2_processor, _wav2vec2_model
        if _wav2vec2_model is None:
            _wav2vec2_processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
            _wav2vec2_model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base-960h")
        audio, sr = librosa.load(audio_path, sr=16000)
        input_values = _wav2vec2_processor(audio, sampling_rate=16000, return_tensors="pt").input_values
        with torch.no_grad():
            emb = _wav2vec2_model(input_values).last_hidden_state.mean(dim=1)
        return emb[0].cpu().numpy().tolist()
    else:
        raise ValueError("Unknown audio model type")

# --- VIDEO EMBEDDING (VideoCLIP) ---
def embed_video(video_path: str) -> list:
    """
    Extract a keyframe using ffmpeg-python and embed with CLIP.
    Args:
        video_path: Path to .mp4 file
    Returns:
        List[float]: Video embedding
    """
    import ffmpeg
    import numpy as np
    from PIL import Image
    import io
    # Probe video for duration
    probe = ffmpeg.probe(video_path)
    duration = float(probe['format']['duration'])
    midpoint = duration / 2
    # Extract frame at midpoint as raw RGB
    out, _ = (
        ffmpeg
        .input(video_path, ss=midpoint)
        .output('pipe:', vframes=1, format='image2', vcodec='png')
        .run(capture_stdout=True, capture_stderr=True)
    )
    img = Image.open(io.BytesIO(out)).convert("RGB")
    return embed_image(img)

# --- FASTEMBED (Local Text Embedding) ---
def embed_text_fast(text: str) -> list:
    """
    Embed text using FastEmbed (local, CPU, no API).
    Args:
        text: Input string
    Returns:
        List[float]: Text embedding
    """
    model = fastembed.TextEmbedding()
    return list(model.embed([text]))[0]

# --- BINARY QUANTIZATION ---
def binary_quantize(vec: list, threshold: float = 0.0) -> str:
    """
    Convert float vector to binary string for memory-efficient storage.
    Args:
        vec: List[float]
        threshold: Threshold for binarization (default 0.0)
    Returns:
        str: Binary string (e.g., '010101...')
    """
    return ''.join(['1' if v > threshold else '0' for v in vec])

# --- Existing code below (text/image embedding, sentiment) ---
    """
    Load and cache the CLIP model for image embeddings.
    Returns:
        SentenceTransformer: The cached CLIP model instance.
    Raises:
        Exception: If model loading fails.
    """
    global _clip_model
    if _clip_model is None:
        try:
            _clip_model = SentenceTransformer("clip-ViT-B-32", device=DEVICE)
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            raise
    return _clip_model
def embed_image(image: Union[str, Image.Image]) -> List[float]:
    """
    Convert an image (file path or PIL Image) to a dense vector embedding using CLIP.
    Args:
        image: Path to image file or PIL Image object.
    Returns:
        List[float]: Vector representation of the image.
    Raises:
        Exception: If embedding generation fails.
    """
    try:
        model = get_clip_model()
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        embedding = model.encode([image], convert_to_numpy=True, show_progress_bar=False)[0]
        return embedding.tolist()
    except Exception as e:
        """
        Embeddings module for PolicyPulse

        Supports multimodal embedding: text, image, audio, code, and structured data.
        All embeddings are evidence-based and used for societal impact analysis.
        """
        logger.error(f"Failed to embed image: {e}")
        raise

def embed_image_batch(images: List[Union[str, Image.Image]]) -> List[List[float]]:
    """
    Convert a batch of images to dense vector embeddings using CLIP.
    Args:
        images: List of image file paths or PIL Image objects.
    Returns:
        List[List[float]]: List of vector representations.
    Raises:
        Exception: If batch embedding fails.
    """
    try:
        pil_images = [Image.open(img).convert("RGB") if isinstance(img, str) else img.convert("RGB") for img in images]
        model = get_clip_model()
        embeddings = model.encode(pil_images, convert_to_numpy=True, show_progress_bar=True)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Failed to batch embed images: {e}")
        raise

# Sentiment label mappings
SENTIMENT_LABELS = ["negative", "neutral", "positive"]
MAX_TOKENIZER_LENGTH = 512


def get_embedding_model() -> SentenceTransformer:
    """
    Load and cache the sentence transformer model.
    
    Returns:
        SentenceTransformer: The cached embedding model instance.
    # No stray docstring here
    Raises:
        Exception: If model loading fails.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model ({EMBEDDING_MODEL}) on device: {DEVICE}")
        try:
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _embedding_model


def get_sentiment_model() -> tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    # Load and cache the sentiment analysis model and tokenizer.
    # Returns: tuple (tokenizer, model) for sentiment classification.
    global _sentiment_tokenizer, _sentiment_model
    if _sentiment_model is None:
        logger.info(f"Loading sentiment model ({SENTIMENT_MODEL}) on device: {DEVICE}")
        try:
            _sentiment_tokenizer = AutoTokenizer.from_pretrained(SENTIMENT_MODEL)
            _sentiment_model = AutoModelForSequenceClassification.from_pretrained(
                SENTIMENT_MODEL
            ).to(DEVICE)
        except Exception as e:
            logger.error(f"Failed to load sentiment model: {e}")
            raise
    return _sentiment_tokenizer, _sentiment_model


def embed_text(text: str) -> List[float]:
    """
    Convert text to a dense vector embedding.
    
    Args:
        text: Input text to embed.
        
    Returns:
        List[float]: Vector representation of the text.
        
    Raises:
        Exception: If embedding generation fails.
    """
    try:
        model = get_embedding_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to embed text: {e}")
        raise


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Convert multiple texts to dense vector embeddings.
    
    Args:
        texts: List of text strings to embed.
        
    Returns:
        List[List[float]]: List of vector representations.
        
    Raises:
        Exception: If batch embedding fails.
    """
    try:
        model = get_embedding_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Failed to batch embed texts: {e}")
        raise


def get_sentiment(text: str) -> str:
    """
    Analyze sentiment of input text.
    
    Args:
        text: Input text to analyze.
        
    Returns:
        str: One of ["negative", "neutral", "positive"].
        
    Raises:
        Exception: If sentiment analysis fails.
    """
    try:
        tokenizer, model = get_sentiment_model()
        
        # Tokenize input with truncation
        token_inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_TOKENIZER_LENGTH
        )
        
        # Move tensors to correct device
        token_inputs = {key: val.to(DEVICE) for key, val in token_inputs.items()}
        
        # Generate predictions
        with torch.no_grad():
            outputs = model(**token_inputs)
            sentiment_scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
            sentiment_scores = sentiment_scores.cpu().numpy()[0]
        
        # Get label with highest confidence
        max_score_idx = sentiment_scores.argmax()
        return SENTIMENT_LABELS[max_score_idx]
        
    except Exception as e:
        logger.error(f"Failed to analyze sentiment: {e}")
        raise
