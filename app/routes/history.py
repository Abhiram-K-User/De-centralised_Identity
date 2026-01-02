"""
DID++ History API
Provides verification history combining SQLite and blockchain data.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.database import get_user_by_did, get_verifications_by_did
from app.services.blockchain import blockchain_service


router = APIRouter()


class VerificationEvent(BaseModel):
    """Single verification event in timeline."""
    event_type: str  # "registration" or "verification"
    timestamp: str
    score: Optional[float] = None
    face_score: Optional[float] = None
    voice_score: Optional[float] = None
    doc_score: Optional[float] = None
    confidence_level: Optional[str] = None
    verified: Optional[bool] = None
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None


class UserHistoryResponse(BaseModel):
    """User history response model."""
    did: str
    user_id: str
    created_at: str
    registration_tx_hash: Optional[str] = None
    timeline: List[VerificationEvent]


@router.get("/user/{did}", response_model=UserHistoryResponse)
async def get_user_history(did: str):
    """
    Get user metadata and verification history.
    
    Combines SQLite metadata with blockchain event logs for a
    chronological timeline of verification attempts.
    
    Args:
        did: Decentralized Identifier to query
    """
    
    # Get user from database
    user = get_user_by_did(did)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DID not found: {did}"
        )
    
    timeline = []
    
    # Add registration event
    registration_event = VerificationEvent(
        event_type="registration",
        timestamp=str(user['created_at']),
        tx_hash=user.get('registration_tx_hash'),
        verified=True
    )
    timeline.append(registration_event)
    
    # Get verification history from database
    db_verifications = get_verifications_by_did(did)
    
    # Get blockchain verification events
    blockchain_verifications = blockchain_service.get_verifications(did)
    
    # Merge database records with blockchain data
    for db_record in db_verifications:
        event = VerificationEvent(
            event_type="verification",
            timestamp=str(db_record['created_at']),
            score=db_record['score'],
            face_score=db_record['face_score'],
            voice_score=db_record['voice_score'],
            doc_score=db_record['doc_score'],
            confidence_level=db_record['confidence_level'],
            verified=db_record['verified'],
            tx_hash=db_record.get('verification_tx_hash')
        )
        
        # Try to find matching blockchain record for block number
        if db_record.get('verification_tx_hash'):
            for bc_record in blockchain_verifications:
                if bc_record.get('tx_hash') == db_record.get('verification_tx_hash'):
                    event.block_number = bc_record.get('block_number')
                    break
        
        timeline.append(event)
    
    # Sort timeline by timestamp (oldest first)
    timeline.sort(key=lambda x: x.timestamp)
    
    return UserHistoryResponse(
        did=did,
        user_id=user['user_id'],
        created_at=str(user['created_at']),
        registration_tx_hash=user.get('registration_tx_hash'),
        timeline=timeline
    )


@router.get("/user/{did}/stats")
async def get_user_stats(did: str):
    """
    Get verification statistics for a user.
    
    Args:
        did: Decentralized Identifier to query
    """
    
    # Get user from database
    user = get_user_by_did(did)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DID not found: {did}"
        )
    
    # Get verification history
    verifications = get_verifications_by_did(did)
    
    total_verifications = len(verifications)
    successful_verifications = sum(1 for v in verifications if v['verified'])
    failed_verifications = total_verifications - successful_verifications
    
    avg_score = 0.0
    if total_verifications > 0:
        avg_score = sum(v['score'] for v in verifications) / total_verifications
    
    return {
        "did": did,
        "user_id": user['user_id'],
        "total_verifications": total_verifications,
        "successful_verifications": successful_verifications,
        "failed_verifications": failed_verifications,
        "average_score": round(avg_score, 4),
        "success_rate": round(successful_verifications / total_verifications, 4) if total_verifications > 0 else 0.0
    }
