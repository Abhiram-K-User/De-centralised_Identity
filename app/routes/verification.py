"""
DID++ Verification API
Handles identity verification with live biometric samples including document OCR.
"""

import json
import time
import numpy as np
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.database import get_user_by_did, log_verification
from app.services.encryption import encryption_service, compute_sha256_bytes
from app.services.ml_engine import ml_engine
from app.services.blockchain import blockchain_service


router = APIRouter()


# Allowed MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg"}
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/wave", "audio/x-wav", "audio/webm", "audio/mpeg", "audio/mp4"}


class VerificationResponse(BaseModel):
    """Verification response model."""
    verified: bool
    final_score: float
    face_score: float
    voice_score: float
    doc_score: float
    doc_text_score: float
    doc_face_score: float
    confidence_level: str
    tx_hash: Optional[str] = None
    message: str


def validate_file(file: UploadFile, allowed_types: set, field_name: str) -> None:
    """Validate file MIME type."""
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} file type. Expected: {allowed_types}, got: {file.content_type}"
        )


async def read_and_validate_file(file: UploadFile, max_size: int = config.MAX_FILE_SIZE) -> bytes:
    """Read file content and validate size."""
    content = await file.read()
    
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {file.filename} exceeds maximum size of {max_size // (1024*1024)}MB"
        )
    
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {file.filename} is empty"
        )
    
    return content


def get_confidence_level(score: float) -> str:
    """Determine confidence level based on score."""
    if score >= 0.90:
        return "VERY_HIGH"
    elif score >= 0.80:
        return "HIGH"
    elif score >= 0.75:
        return "MEDIUM"
    else:
        return "LOW"


def bytes_to_embedding(data: bytes, dtype=np.float32) -> np.ndarray:
    """Convert bytes to numpy embedding array."""
    return np.frombuffer(data, dtype=dtype)


def text_similarity(text1: str, text2: str) -> float:
    """
    Compute text similarity using multiple methods.
    Combines Jaccard similarity with character-level matching.
    """
    if not text1 or not text2:
        return 0.0
    
    # Normalize text
    text1_normalized = text1.lower().strip()
    text2_normalized = text2.lower().strip()
    
    # Word-level Jaccard similarity
    words1 = set(text1_normalized.split())
    words2 = set(text2_normalized.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Character n-gram similarity (more robust to OCR errors)
    def get_ngrams(text, n=3):
        text = text.replace(" ", "")
        return set(text[i:i+n] for i in range(len(text) - n + 1))
    
    ngrams1 = get_ngrams(text1_normalized)
    ngrams2 = get_ngrams(text2_normalized)
    
    if not ngrams1 or not ngrams2:
        return jaccard
    
    ngram_intersection = ngrams1.intersection(ngrams2)
    ngram_union = ngrams1.union(ngrams2)
    ngram_similarity = len(ngram_intersection) / len(ngram_union) if ngram_union else 0.0
    
    # Combine scores (weighted average)
    return 0.6 * ngram_similarity + 0.4 * jaccard


def create_verification_payload(
    did: str,
    face_score: float,
    voice_score: float,
    doc_score: float,
    final_score: float,
    verified: bool,
    timestamp: int
) -> dict:
    """Create verification payload for blockchain."""
    return {
        "action": "verify",
        "did": did,
        "scores": {
            "face": face_score,
            "voice": voice_score,
            "document": doc_score,
            "final": final_score
        },
        "verified": verified,
        "timestamp": timestamp
    }


@router.post("/verify", response_model=VerificationResponse)
async def verify_identity(
    did: str = Form(..., description="DID to verify against"),
    face: UploadFile = File(..., description="Live face image (JPEG)"),
    voice: UploadFile = File(..., description="Live voice sample (WAV)"),
    id_doc: UploadFile = File(None, description="Live ID document image (JPEG) - optional")
):
    """
    Verify identity against stored biometric data.
    
    Accepts multipart/form-data with:
    - did: Decentralized Identifier to verify against
    - face: Live face image (JPEG)
    - voice: Live voice sample (WAV)
    - id_doc: Live ID document image (JPEG) - optional for enhanced verification
    
    Returns verification result with scores and confidence level.
    """
    
    # Get stored user data
    user = get_user_by_did(did)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DID not found: {did}"
        )
    
    # Validate file types
    validate_file(face, ALLOWED_IMAGE_TYPES, "face")
    validate_file(voice, ALLOWED_AUDIO_TYPES, "voice")
    
    # Read file contents
    face_bytes = await read_and_validate_file(face)
    voice_bytes = await read_and_validate_file(voice)
    
    # Process live biometrics
    live_face_embedding = ml_engine.process_face(face_bytes)
    if live_face_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect face in the live image"
        )
    
    live_voice_embedding = ml_engine.process_voice(voice_bytes)
    if live_voice_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not process live voice sample"
        )
    
    # Decrypt stored embeddings
    stored_face_bytes = encryption_service.decrypt_embedding(user['face_embedding'])
    stored_voice_bytes = encryption_service.decrypt_embedding(user['voice_embedding'])
    stored_doc_bytes = encryption_service.decrypt_embedding(user['doc_embedding'])
    
    # Convert to numpy arrays
    stored_face_embedding = bytes_to_embedding(stored_face_bytes)
    stored_voice_embedding = bytes_to_embedding(stored_voice_bytes)
    stored_doc_embedding = bytes_to_embedding(stored_doc_bytes)
    
    # Compute face similarity (cosine)
    face_score = ml_engine.cosine_similarity(live_face_embedding, stored_face_embedding)
    face_score = max(0.0, min(1.0, face_score))  # Clamp to [0, 1]
    
    # Compute voice similarity (cosine)
    voice_score = ml_engine.cosine_similarity(live_voice_embedding, stored_voice_embedding)
    voice_score = max(0.0, min(1.0, voice_score))  # Clamp to [0, 1]
    
    # Document verification
    doc_text_score = 0.0
    doc_face_score = 0.0
    
    if id_doc and id_doc.filename:
        # User provided live document - do full document verification
        validate_file(id_doc, ALLOWED_IMAGE_TYPES, "id_doc")
        doc_bytes = await read_and_validate_file(id_doc)
        
        # Extract text and face from live document
        live_doc_embedding, live_doc_text = ml_engine.process_document(doc_bytes)
        
        # Compare extracted text with stored text
        stored_doc_text = user.get('doc_text', '')
        doc_text_score = text_similarity(live_doc_text, stored_doc_text)
        
        # Compare face in live document with stored face
        if live_doc_embedding is not None:
            # Extract face portion from document embedding (first 512 dims)
            live_doc_face = live_doc_embedding[:512] if len(live_doc_embedding) >= 512 else live_doc_embedding
            
            # Compare with stored face embedding for face-to-document match
            doc_face_score = ml_engine.cosine_similarity(live_face_embedding, live_doc_face)
            doc_face_score = max(0.0, min(1.0, doc_face_score))
        
        # Combined document score: 50% text match + 50% face match
        doc_score = 0.5 * doc_text_score + 0.5 * doc_face_score
    else:
        # No live document provided - use stored document face against live face
        # Document embedding: first 512 dims are face (ArcFace), next 128 are text
        doc_face_portion = stored_doc_embedding[:512]
        
        # Pad if necessary
        if len(doc_face_portion) < 512:
            doc_face_portion = np.pad(doc_face_portion, (0, 512 - len(doc_face_portion)))
        
        live_face_normalized = live_face_embedding[:512] if len(live_face_embedding) >= 512 else live_face_embedding
        if len(live_face_normalized) < 512:
            live_face_normalized = np.pad(live_face_normalized, (0, 512 - len(live_face_normalized)))
        
        doc_face_score = ml_engine.cosine_similarity(live_face_normalized, doc_face_portion)
        doc_face_score = max(0.0, min(1.0, doc_face_score))
        
        # Text score defaults to stored (assume valid from registration)
        doc_text_score = 1.0
        
        doc_score = 0.5 * doc_text_score + 0.5 * doc_face_score
    
    # Weighted fusion
    final_score = (
        config.FACE_WEIGHT * face_score +
        config.VOICE_WEIGHT * voice_score +
        config.DOC_WEIGHT * doc_score
    )
    
    # Determine verification status
    verified = final_score >= config.VERIFICATION_THRESHOLD
    confidence_level = get_confidence_level(final_score)
    
    # Prepare response
    tx_hash = None
    
    # Log to blockchain if verified
    if verified:
        timestamp = int(time.time())
        payload = create_verification_payload(
            did, face_score, voice_score, doc_score,
            final_score, verified, timestamp
        )
        payload_json = json.dumps(payload, sort_keys=True)
        verification_hash = compute_sha256_bytes(payload_json)
        
        tx_hash = blockchain_service.log_verification(verification_hash, did)
    
    # Log verification attempt to database
    log_verification(
        did=did,
        score=final_score,
        face_score=face_score,
        voice_score=voice_score,
        doc_score=doc_score,
        confidence_level=confidence_level,
        verified=verified,
        verification_tx_hash=tx_hash
    )
    
    message = "Identity verified successfully" if verified else "Identity verification failed"
    
    return VerificationResponse(
        verified=verified,
        final_score=round(final_score, 4),
        face_score=round(face_score, 4),
        voice_score=round(voice_score, 4),
        doc_score=round(doc_score, 4),
        doc_text_score=round(doc_text_score, 4),
        doc_face_score=round(doc_face_score, 4),
        confidence_level=confidence_level,
        tx_hash=tx_hash,
        message=message
    )
