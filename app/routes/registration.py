"""
DID++ Registration API
Handles user registration with multimodal biometric data.
"""

import json
import time
import uuid
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.database import create_user
from app.services.encryption import encryption_service, compute_sha256, compute_sha256_bytes
from app.services.ml_engine import ml_engine
from app.services.blockchain import blockchain_service


router = APIRouter()


# Allowed MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg"}
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/wave", "audio/x-wav", "audio/webm", "audio/mpeg", "audio/mp4"}


class RegistrationResponse(BaseModel):
    """Registration response model."""
    success: bool
    did: str
    user_id: str
    tx_hash: Optional[str] = None
    message: str


def validate_file(file: UploadFile, allowed_types: set, field_name: str) -> None:
    """Validate file MIME type and size."""
    # Check MIME type
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


def generate_user_id() -> str:
    """Auto-generate a unique user ID."""
    return f"user_{uuid.uuid4().hex[:12]}"


def generate_did(user_id: str) -> str:
    """Generate a DID string."""
    unique_id = uuid.uuid4().hex[:16]
    return f"did:eth:sepolia:{user_id}:{unique_id}"


def create_registration_payload(
    face_hash: str,
    voice_hash: str,
    doc_hash: str,
    timestamp: int
) -> dict:
    """Create registration payload for blockchain."""
    return {
        "action": "register",
        "model_version": "1.0.0",
        "evidence_hashes": {
            "face": face_hash,
            "voice": voice_hash,
            "document": doc_hash
        },
        "timestamp": timestamp
    }


@router.post("/register", response_model=RegistrationResponse)
async def register_user(
    face: UploadFile = File(..., description="Face image (JPEG, max 10MB)"),
    voice: UploadFile = File(..., description="Voice sample (WAV/WebM, max 10MB)"),
    id_doc: UploadFile = File(..., description="ID document image (JPEG, max 10MB)")
):
    """
    Register a new user with multimodal biometric data.
    
    Accepts multipart/form-data with:
    - face: Face image (JPEG)
    - voice: Voice sample (WAV or WebM)
    - id_doc: ID document image (JPEG)
    
    User ID is auto-generated.
    """
    
    # Auto-generate user ID
    user_id = generate_user_id()
    
    # Validate file types
    validate_file(face, ALLOWED_IMAGE_TYPES, "face")
    validate_file(voice, ALLOWED_AUDIO_TYPES, "voice")
    validate_file(id_doc, ALLOWED_IMAGE_TYPES, "id_doc")
    
    # Read file contents
    face_bytes = await read_and_validate_file(face)
    voice_bytes = await read_and_validate_file(voice)
    doc_bytes = await read_and_validate_file(id_doc)
    
    # Process biometrics through ML engine
    face_embedding = ml_engine.process_face(face_bytes)
    if face_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect face in the uploaded image"
        )
    
    voice_embedding = ml_engine.process_voice(voice_bytes)
    if voice_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not process voice sample"
        )
    
    doc_embedding, doc_text = ml_engine.process_document(doc_bytes)
    if doc_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not process ID document"
        )
    
    # Generate DID
    did = generate_did(user_id)
    
    # Compute SHA256 hashes of evidence files
    face_hash = compute_sha256(face_bytes)
    voice_hash = compute_sha256(voice_bytes)
    doc_hash = compute_sha256(doc_bytes)
    
    # Create registration payload
    timestamp = int(time.time())
    payload = create_registration_payload(face_hash, voice_hash, doc_hash, timestamp)
    
    # Hash payload to create identity_hash (32 bytes)
    payload_json = json.dumps(payload, sort_keys=True)
    identity_hash = compute_sha256_bytes(payload_json)
    
    # Encrypt embeddings before storage
    encrypted_face = encryption_service.encrypt_embedding(face_embedding.tobytes())
    encrypted_voice = encryption_service.encrypt_embedding(voice_embedding.tobytes())
    encrypted_doc = encryption_service.encrypt_embedding(doc_embedding.tobytes())
    
    # Register on blockchain
    tx_hash = blockchain_service.register_did(identity_hash, did)
    
    # Store in database
    success = create_user(
        user_id=user_id,
        did=did,
        face_embedding=encrypted_face,
        voice_embedding=encrypted_voice,
        doc_embedding=encrypted_doc,
        doc_text=doc_text,
        registration_tx_hash=tx_hash or ""
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store user data"
        )
    
    return RegistrationResponse(
        success=True,
        did=did,
        user_id=user_id,
        tx_hash=tx_hash,
        message="Registration successful"
    )
