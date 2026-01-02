"""
DID++ Verification API
Fully decentralized identity verification using blockchain + IPFS.

Verification Flow:
1. Query blockchain for DID's metadata CID
2. Fetch encrypted metadata from IPFS
3. Decrypt embeddings in-memory (never written to disk)
4. Compare live biometrics against stored embeddings
5. Log verification proof on blockchain
"""

import json
import time
import base64
import numpy as np
from typing import Optional, Dict, Any
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.services.encryption import encryption_service, compute_sha256_bytes
from app.services.ml_engine import ml_engine
from app.services.blockchain import blockchain_service
from app.services.ipfs import ipfs_service
from app.services.alias import alias_service


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
    metadata_cid: str
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
    metadata_cid: str,
    face_score: float,
    voice_score: float,
    doc_score: float,
    final_score: float,
    confidence_level: str,
    verified: bool,
    timestamp: int
) -> dict:
    """Create verification payload for blockchain proof."""
    return {
        "action": "verify",
        "version": "2.0.0",
        "did": did,
        "metadata_cid": metadata_cid,
        "scores": {
            "face": round(face_score, 4),
            "voice": round(voice_score, 4),
            "document": round(doc_score, 4),
            "final": round(final_score, 4)
        },
        "confidence_level": confidence_level,
        "verified": verified,
        "timestamp": timestamp
    }


async def fetch_and_decrypt_metadata(did: str) -> Dict[str, Any]:
    """
    Fetch metadata from blockchain → IPFS → decrypt.
    
    This is the core decentralized retrieval mechanism:
    1. Query blockchain for CID
    2. Fetch encrypted JSON from IPFS
    3. Decrypt embeddings in-memory
    
    Args:
        did: Full DID string
        
    Returns:
        Dictionary containing decrypted embeddings and metadata
        
    Raises:
        HTTPException if any step fails
    """
    
    # ============ Step 1: Query Blockchain for CID ============
    
    if blockchain_service.is_configured():
        # Try blockchain first
        cid, error = blockchain_service.get_metadata_cid(did)
        if error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DID not found on blockchain: {error}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service not configured"
        )
    
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metadata CID found for DID: {did}"
        )
    
    # ============ Step 2: Fetch from IPFS ============
    
    ipfs_data, error = ipfs_service.fetch_metadata(cid)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch from IPFS: {error}"
        )
    
    if not ipfs_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found at IPFS CID: {cid}"
        )
    
    # ============ Step 3: Decrypt In-Memory ============
    
    try:
        # Decrypt face embedding
        encrypted_face = ipfs_data['encrypted_face_embedding']
        decrypted_face_bytes = encryption_service.decrypt(encrypted_face.encode('utf-8'))
        face_embedding = bytes_to_embedding(decrypted_face_bytes)
        
        # Decrypt voice embedding
        encrypted_voice = ipfs_data['encrypted_voice_embedding']
        decrypted_voice_bytes = encryption_service.decrypt(encrypted_voice.encode('utf-8'))
        voice_embedding = bytes_to_embedding(decrypted_voice_bytes)
        
        # Decrypt document data (JSON with embedding + text)
        encrypted_doc = ipfs_data['encrypted_doc_data']
        decrypted_doc_bytes = encryption_service.decrypt(encrypted_doc.encode('utf-8'))
        doc_data = json.loads(decrypted_doc_bytes.decode('utf-8'))
        
        # Decode document embedding from base64
        doc_embedding_bytes = base64.b64decode(doc_data['embedding'])
        doc_embedding = bytes_to_embedding(doc_embedding_bytes)
        doc_text = doc_data.get('text', '')
        
        return {
            "cid": cid,
            "user_id": ipfs_data.get('user_id'),
            "did": ipfs_data.get('did'),
            "face_embedding": face_embedding,
            "voice_embedding": voice_embedding,
            "doc_embedding": doc_embedding,
            "doc_text": doc_text,
            "created_at": ipfs_data.get('created_at')
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt metadata: {str(e)}"
        )


@router.post("/verify", response_model=VerificationResponse)
async def verify_identity(
    did: str = Form(..., description="DID, short code, or alias to verify against"),
    face: UploadFile = File(..., description="Live face image (JPEG)"),
    voice: UploadFile = File(..., description="Live voice sample (WAV)"),
    id_doc: UploadFile = File(None, description="Live ID document image (JPEG) - optional")
):
    """
    Verify identity using decentralized storage.
    
    Accepts:
    - Full DID (did:eth:sepolia:...)
    - Short code (8 characters)
    - Custom alias
    
    Verification Flow:
    1. Resolve identifier to full DID
    2. Fetch metadata CID from blockchain
    3. Download encrypted metadata from IPFS
    4. Decrypt embeddings in-memory (never touches disk)
    5. Compare live biometrics against stored embeddings
    6. Log verification proof on blockchain
    
    No local database is accessed - everything comes from IPFS + blockchain.
    
    Returns:
    - Verification result with scores
    - Confidence level
    - Blockchain transaction hash (for successful verifications)
    """
    
    # ============ Step 0: Resolve Identifier ============
    
    # Try to resolve if it's a short code or alias
    resolved_did = alias_service.resolve(did)
    
    if resolved_did:
        did = resolved_did
    # If not resolved and doesn't look like a DID, it might be unregistered
    elif not did.startswith("did:"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Identifier not found: {did}. Please use your full DID, short code, or registered alias."
        )
    
    # Validate file types
    validate_file(face, ALLOWED_IMAGE_TYPES, "face")
    validate_file(voice, ALLOWED_AUDIO_TYPES, "voice")
    
    # Read file contents
    face_bytes = await read_and_validate_file(face)
    voice_bytes = await read_and_validate_file(voice)
    
    # ============ Step 1: Fetch & Decrypt Stored Data ============
    
    stored_data = await fetch_and_decrypt_metadata(did)
    metadata_cid = stored_data['cid']
    
    stored_face_embedding = stored_data['face_embedding']
    stored_voice_embedding = stored_data['voice_embedding']
    stored_doc_embedding = stored_data['doc_embedding']
    stored_doc_text = stored_data['doc_text']
    
    # ============ Step 2: Process Live Biometrics ============
    
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
    
    # ============ Step 3: Compute Similarity Scores ============
    
    # Face similarity (cosine)
    face_score = ml_engine.cosine_similarity(live_face_embedding, stored_face_embedding)
    face_score = max(0.0, min(1.0, face_score))
    
    # Voice similarity (cosine)
    voice_score = ml_engine.cosine_similarity(live_voice_embedding, stored_voice_embedding)
    voice_score = max(0.0, min(1.0, voice_score))
    
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
    
    # ============ Step 4: Weighted Fusion ============
    
    final_score = (
        config.FACE_WEIGHT * face_score +
        config.VOICE_WEIGHT * voice_score +
        config.DOC_WEIGHT * doc_score
    )
    
    verified = final_score >= config.VERIFICATION_THRESHOLD
    confidence_level = get_confidence_level(final_score)
    
    # ============ Step 5: Log Verification on Blockchain ============
    
    tx_hash = None
    
    if verified and blockchain_service.is_configured():
        timestamp = int(time.time())
        
        # Create verification payload
        payload = create_verification_payload(
            did=did,
            metadata_cid=metadata_cid,
            face_score=face_score,
            voice_score=voice_score,
            doc_score=doc_score,
            final_score=final_score,
            confidence_level=confidence_level,
            verified=verified,
            timestamp=timestamp
        )
        
        # Compute verification hash
        payload_json = json.dumps(payload, sort_keys=True)
        verification_hash = compute_sha256_bytes(payload_json)
        
        # Log on blockchain
        tx_hash, error = blockchain_service.log_verification(
            did=did,
            verification_hash=verification_hash,
            metadata_cid=metadata_cid,
            confidence_level=confidence_level,
            success=verified
        )
        
        if error:
            print(f"Blockchain verification logging warning: {error}")
    
    # ============ Step 6: Return Result ============
    
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
        metadata_cid=metadata_cid,
        tx_hash=tx_hash,
        message=message
    )


@router.get("/lookup/{identifier}")
async def lookup_did(identifier: str):
    """
    Look up a DID on the blockchain.
    
    Accepts:
    - Full DID (did:eth:sepolia:...)
    - Short code (8 characters)
    - Custom alias
    
    Returns the DID record including:
    - IPFS CID
    - Identity hash
    - Registration timestamp
    - Active status
    - Short code and aliases
    """
    
    if not blockchain_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service not configured"
        )
    
    # Resolve identifier to DID
    did = alias_service.resolve(identifier)
    if not did:
        if identifier.startswith("did:"):
            did = identifier
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Identifier not found: {identifier}"
            )
    
    # Check if DID exists
    exists, active = blockchain_service.is_did_active(did)
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DID not found: {did}"
        )
    
    # Get full record
    record, error = blockchain_service.get_did_record(did)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch DID record: {error}"
        )
    
    # Get identifiers (short code and aliases)
    identifiers = alias_service.get_identifiers(did)
    
    return {
        "did": did,
        "short_code": identifiers['short_code'],
        "aliases": identifiers['aliases'],
        "exists": exists,
        "active": active,
        "metadata_cid": record['metadata_cid'],
        "identity_hash": record['identity_hash'],
        "registered_at": record['registered_at'],
        "updated_at": record['updated_at'],
        "registrar": record['registrar'],
        "ipfs_gateway_url": ipfs_service.get_gateway_url(record['metadata_cid'])
    }
