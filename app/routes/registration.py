"""
DID++ Registration API
Fully decentralized user registration with IPFS storage and blockchain anchoring.

Data Flow:
1. Receive biometric files (~4MB total)
2. Extract embeddings via ML engine
3. Encrypt embeddings with AES-256-CBC
4. Bundle into JSON metadata (~5KB)
5. Upload to IPFS, get CID
6. Register on blockchain (CID + 32-byte hash)
"""

import json
import time
import uuid
import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.services.encryption import encryption_service, compute_sha256, compute_sha256_bytes
from app.services.ml_engine import ml_engine
from app.services.blockchain import blockchain_service
from app.services.ipfs import ipfs_service, create_ipfs_metadata
from app.services.alias import alias_service


router = APIRouter()


# Allowed MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg"}
ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/wave", "audio/x-wav", "audio/webm", "audio/mpeg", "audio/mp4"}


class DataReductionStats(BaseModel):
    """Data reduction pipeline statistics."""
    raw_total_bytes: int
    raw_total_kb: float
    raw_total_mb: float
    encrypted_metadata_bytes: int
    encrypted_metadata_kb: float
    blockchain_hash_bytes: int
    reduction_raw_to_ipfs: str
    reduction_raw_to_blockchain: str
    storage_saved_percent: float


class RegistrationResponse(BaseModel):
    """Registration response model."""
    success: bool
    did: str
    short_code: str  # User-friendly 8-char code
    user_id: str
    ipfs_cid: str
    ipfs_gateway_url: str
    identity_hash: str
    tx_hash: Optional[str] = None
    data_reduction: DataReductionStats
    message: str


def validate_file(file: UploadFile, allowed_types: set, field_name: str) -> None:
    """Validate file MIME type and size."""
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
    """Generate a DID string following did:eth:sepolia method."""
    unique_id = uuid.uuid4().hex[:16]
    return f"did:eth:sepolia:{user_id}:{unique_id}"


def create_registration_payload(
    user_id: str,
    did: str,
    face_hash: str,
    voice_hash: str,
    doc_hash: str,
    ipfs_cid: str,
    timestamp: int
) -> dict:
    """Create registration payload for identity hash computation."""
    return {
        "action": "register",
        "version": "2.0.0",
        "user_id": user_id,
        "did": did,
        "evidence_hashes": {
            "face": face_hash,
            "voice": voice_hash,
            "document": doc_hash
        },
        "ipfs_cid": ipfs_cid,
        "timestamp": timestamp
    }


def calculate_data_reduction(
    raw_face_size: int,
    raw_voice_size: int,
    raw_doc_size: int,
    encrypted_size: int
) -> DataReductionStats:
    """Calculate data reduction statistics."""
    total_raw = raw_face_size + raw_voice_size + raw_doc_size
    hash_size = 32  # SHA-256
    
    raw_to_ipfs = total_raw / encrypted_size if encrypted_size > 0 else 0
    raw_to_hash = total_raw / hash_size
    saved_percent = (1 - encrypted_size / total_raw) * 100 if total_raw > 0 else 0
    
    return DataReductionStats(
        raw_total_bytes=total_raw,
        raw_total_kb=round(total_raw / 1024, 2),
        raw_total_mb=round(total_raw / (1024 * 1024), 2),
        encrypted_metadata_bytes=encrypted_size,
        encrypted_metadata_kb=round(encrypted_size / 1024, 2),
        blockchain_hash_bytes=hash_size,
        reduction_raw_to_ipfs=f"{raw_to_ipfs:.0f}x",
        reduction_raw_to_blockchain=f"{raw_to_hash:.0f}x",
        storage_saved_percent=round(saved_percent, 2)
    )


@router.post("/register", response_model=RegistrationResponse)
async def register_user(
    face: UploadFile = File(..., description="Face image (JPEG, max 10MB)"),
    voice: UploadFile = File(..., description="Voice sample (WAV/WebM, max 10MB)"),
    id_doc: UploadFile = File(..., description="ID document image (JPEG, max 10MB)")
):
    """
    Register a new user with fully decentralized identity storage.
    
    Process:
    1. Extract biometric embeddings from uploaded files
    2. Encrypt embeddings using AES-256-CBC
    3. Bundle encrypted data into IPFS metadata JSON
    4. Upload to IPFS via Pinata
    5. Register on Ethereum Sepolia blockchain
    
    No local database is used - all data is stored on IPFS with blockchain anchoring.
    
    Returns:
    - DID (Decentralized Identifier)
    - IPFS CID (Content Identifier)
    - Blockchain transaction hash
    - Data reduction statistics
    """
    
    # Check service configuration
    if not ipfs_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IPFS service not configured. Please set Pinata credentials."
        )
    
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
    
    # Track raw sizes for data reduction stats
    raw_face_size = len(face_bytes)
    raw_voice_size = len(voice_bytes)
    raw_doc_size = len(doc_bytes)
    
    # ============ Step 1: Process Biometrics ============
    
    # Process face through ML engine (extracts 512-D ArcFace embedding)
    face_embedding = ml_engine.process_face(face_bytes)
    if face_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect face in the uploaded image"
        )
    
    # Process voice through ML engine (extracts 192-D ECAPA-TDNN embedding)
    voice_embedding = ml_engine.process_voice(voice_bytes)
    if voice_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not process voice sample"
        )
    
    # Process document through ML engine (extracts 640-D combined embedding + OCR text)
    doc_embedding, doc_text = ml_engine.process_document(doc_bytes)
    if doc_embedding is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not process ID document"
        )
    
    # ============ Step 2: Encrypt Embeddings ============
    
    # Encrypt face embedding
    encrypted_face = encryption_service.encrypt_embedding(face_embedding.tobytes())
    
    # Encrypt voice embedding
    encrypted_voice = encryption_service.encrypt_embedding(voice_embedding.tobytes())
    
    # Encrypt document data (embedding + text as JSON)
    doc_data = {
        "embedding": base64.b64encode(doc_embedding.tobytes()).decode('utf-8'),
        "text": doc_text
    }
    doc_data_json = json.dumps(doc_data)
    encrypted_doc = encryption_service.encrypt(doc_data_json.encode('utf-8'))
    
    # ============ Step 3: Generate DID ============
    
    did = generate_did(user_id)
    
    # Compute SHA256 hashes of raw evidence files
    face_hash = compute_sha256(face_bytes)
    voice_hash = compute_sha256(voice_bytes)
    doc_hash = compute_sha256(doc_bytes)
    
    # ============ Step 4: Create & Upload IPFS Metadata ============
    
    # Create preliminary identity hash (will be updated with CID)
    timestamp = int(time.time())
    preliminary_payload = {
        "user_id": user_id,
        "did": did,
        "evidence_hashes": {
            "face": face_hash,
            "voice": voice_hash,
            "document": doc_hash
        },
        "timestamp": timestamp
    }
    preliminary_hash = compute_sha256(json.dumps(preliminary_payload, sort_keys=True))
    
    # Create IPFS metadata object
    ipfs_metadata = create_ipfs_metadata(
        user_id=user_id,
        did=did,
        encrypted_face=encrypted_face.decode('utf-8'),
        encrypted_voice=encrypted_voice.decode('utf-8'),
        encrypted_doc=encrypted_doc.decode('utf-8'),
        identity_hash=preliminary_hash
    )
    
    # Upload to IPFS
    upload_result = ipfs_service.upload_metadata(
        metadata=ipfs_metadata,
        pin_name=f"did-{user_id}"
    )
    
    if not upload_result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"IPFS upload failed: {upload_result.error}"
        )
    
    ipfs_cid = upload_result.cid
    encrypted_size = upload_result.size_bytes
    
    # ============ Step 5: Create Final Identity Hash ============
    
    # Now create the final registration payload with the CID
    final_payload = create_registration_payload(
        user_id=user_id,
        did=did,
        face_hash=face_hash,
        voice_hash=voice_hash,
        doc_hash=doc_hash,
        ipfs_cid=ipfs_cid,
        timestamp=timestamp
    )
    
    # Compute final 32-byte identity hash
    payload_json = json.dumps(final_payload, sort_keys=True)
    identity_hash = compute_sha256_bytes(payload_json)
    identity_hash_hex = identity_hash.hex()
    
    # ============ Step 6: Register on Blockchain ============
    
    tx_hash = None
    blockchain_error = None
    
    if blockchain_service.is_configured():
        tx_hash, blockchain_error = blockchain_service.register_did(
            did=did,
            metadata_cid=ipfs_cid,
            identity_hash=identity_hash
        )
        
        if blockchain_error:
            # Log but don't fail - IPFS storage is primary
            print(f"Blockchain registration warning: {blockchain_error}")
    else:
        print("Blockchain not configured - skipping on-chain registration")
    
    # ============ Step 7: Calculate Data Reduction Stats ============
    
    data_reduction = calculate_data_reduction(
        raw_face_size=raw_face_size,
        raw_voice_size=raw_voice_size,
        raw_doc_size=raw_doc_size,
        encrypted_size=encrypted_size
    )
    
    # ============ Step 8: Generate Short Code ============
    
    # Generate and register user-friendly short code
    short_code = alias_service.register_short_code(did)
    
    return RegistrationResponse(
        success=True,
        did=did,
        short_code=short_code,
        user_id=user_id,
        ipfs_cid=ipfs_cid,
        ipfs_gateway_url=upload_result.gateway_url,
        identity_hash=identity_hash_hex,
        tx_hash=tx_hash,
        data_reduction=data_reduction,
        message=f"Registration successful! Your short code: {short_code}"
    )


@router.get("/status")
async def get_registration_status():
    """
    Get status of decentralized services.
    
    Returns configuration and connectivity status for:
    - IPFS (Pinata)
    - Blockchain (Ethereum Sepolia)
    - Encryption
    """
    blockchain_stats = blockchain_service.get_stats()
    
    return {
        "ipfs": {
            "configured": ipfs_service.is_configured(),
            "gateway": config.IPFS_GATEWAY
        },
        "blockchain": blockchain_stats,
        "encryption": {
            "configured": config.is_encryption_configured(),
            "algorithm": "AES-256-CBC"
        },
        "data_reduction": {
            "target_ipfs_kb": config.TARGET_IPFS_SIZE_KB,
            "blockchain_bytes": config.BLOCKCHAIN_HASH_BYTES,
            "expected_reduction": "~800x to IPFS, ~125000x to blockchain"
        }
    }
