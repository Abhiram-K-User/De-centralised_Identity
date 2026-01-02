"""
DID++ History API
Fully decentralized history retrieval using blockchain event logs.

No database queries - all history is reconstructed from:
- DIDRegistered events from DIDRegistry contract
- VerificationLogged events from VerificationLog contract
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.config import config
from app.services.blockchain import blockchain_service
from app.services.ipfs import ipfs_service
from app.services.alias import alias_service


router = APIRouter()


class TimelineEvent(BaseModel):
    """Single event in the identity timeline."""
    event_type: str  # "registration" or "verification"
    timestamp: int  # Unix timestamp
    timestamp_formatted: str  # Human-readable
    did: str
    tx_hash: str
    block_number: int
    # Registration-specific fields
    metadata_cid: Optional[str] = None
    identity_hash: Optional[str] = None
    registrar: Optional[str] = None
    # Verification-specific fields
    verification_hash: Optional[str] = None
    confidence_level: Optional[str] = None
    success: Optional[bool] = None
    verifier: Optional[str] = None


class UserHistoryResponse(BaseModel):
    """User history response model."""
    did: str
    exists: bool
    active: bool
    metadata_cid: str
    ipfs_gateway_url: str
    identity_hash: str
    registered_at: int
    registered_at_formatted: str
    registrar: str
    verification_count: int
    timeline: List[TimelineEvent]


class StatsResponse(BaseModel):
    """DID statistics response."""
    did: str
    total_verifications: int
    successful_verifications: int
    failed_verifications: int
    success_rate: float
    last_verification_at: Optional[int] = None
    last_verification_formatted: Optional[str] = None


def format_timestamp(ts: int) -> str:
    """Format Unix timestamp to human-readable string."""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return str(ts)


@router.get("/user/{identifier}", response_model=UserHistoryResponse)
async def get_user_history(identifier: str):
    """
    Get user identity history from blockchain.
    
    Accepts:
    - Full DID (did:eth:sepolia:...)
    - Short code (8 characters)
    - Custom alias
    
    Reconstructs the full timeline by querying blockchain event logs:
    - DIDRegistered events for registration
    - VerificationLogged events for verification attempts
    
    No database is queried - all data comes from the blockchain.
    
    Args:
        identifier: DID, short code, or alias to query
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
    
    # Get DID record from blockchain
    record, error = blockchain_service.get_did_record(did)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch DID record: {error}"
        )
    
    # Get full timeline from blockchain events
    timeline_events = blockchain_service.get_full_timeline(did)
    
    # Convert to TimelineEvent models
    timeline = []
    for event in timeline_events:
        if event['event_type'] == 'registration':
            timeline.append(TimelineEvent(
                event_type="registration",
                timestamp=event['timestamp'],
                timestamp_formatted=format_timestamp(event['timestamp']),
                did=event['did'],
                tx_hash=event['tx_hash'],
                block_number=event['block_number'],
                metadata_cid=event.get('metadata_cid'),
                identity_hash=event.get('identity_hash'),
                registrar=event.get('registrar')
            ))
        elif event['event_type'] == 'verification':
            timeline.append(TimelineEvent(
                event_type="verification",
                timestamp=event['timestamp'],
                timestamp_formatted=format_timestamp(event['timestamp']),
                did=event['did'],
                tx_hash=event['tx_hash'],
                block_number=event['block_number'],
                metadata_cid=event.get('metadata_cid'),
                verification_hash=event.get('verification_hash'),
                confidence_level=event.get('confidence_level'),
                success=event.get('success'),
                verifier=event.get('verifier')
            ))
    
    # Get verification count
    verification_count = blockchain_service.get_verification_count(did)
    
    return UserHistoryResponse(
        did=did,
        exists=exists,
        active=active,
        metadata_cid=record['metadata_cid'],
        ipfs_gateway_url=ipfs_service.get_gateway_url(record['metadata_cid']),
        identity_hash=record['identity_hash'],
        registered_at=record['registered_at'],
        registered_at_formatted=format_timestamp(record['registered_at']),
        registrar=record['registrar'],
        verification_count=verification_count,
        timeline=timeline
    )


@router.get("/user/{identifier}/stats", response_model=StatsResponse)
async def get_user_stats(identifier: str):
    """
    Get verification statistics for a DID.
    
    Accepts:
    - Full DID (did:eth:sepolia:...)
    - Short code (8 characters)
    - Custom alias
    
    Queries blockchain for verification events and computes:
    - Total verifications
    - Successful vs failed
    - Success rate
    - Last verification timestamp
    
    Args:
        identifier: DID, short code, or alias to query
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
    exists, _ = blockchain_service.is_did_active(did)
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DID not found: {did}"
        )
    
    # Get verification events
    verifications = blockchain_service.get_verification_events(did)
    
    total = len(verifications)
    successful = sum(1 for v in verifications if v.get('success'))
    failed = total - successful
    success_rate = successful / total if total > 0 else 0.0
    
    # Get last verification
    last_verification_at = None
    last_verification_formatted = None
    
    if verifications:
        # Sort by timestamp descending
        sorted_verifications = sorted(verifications, key=lambda x: x['timestamp'], reverse=True)
        last_verification_at = sorted_verifications[0]['timestamp']
        last_verification_formatted = format_timestamp(last_verification_at)
    
    return StatsResponse(
        did=did,
        total_verifications=total,
        successful_verifications=successful,
        failed_verifications=failed,
        success_rate=round(success_rate, 4),
        last_verification_at=last_verification_at,
        last_verification_formatted=last_verification_formatted
    )


@router.get("/user/{identifier}/verifications")
async def get_verifications(
    identifier: str,
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get recent verification records for a DID.
    
    Accepts:
    - Full DID (did:eth:sepolia:...)
    - Short code (8 characters)
    - Custom alias
    
    Args:
        identifier: DID, short code, or alias to query
        limit: Maximum number of records to return (1-100)
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
    exists, _ = blockchain_service.is_did_active(did)
    
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DID not found: {did}"
        )
    
    # Get recent verifications from contract
    records = blockchain_service.get_recent_verifications(did, limit)
    
    # Enrich with formatted timestamps
    for record in records:
        record['timestamp_formatted'] = format_timestamp(record['timestamp'])
    
    return {
        "did": did,
        "total_count": blockchain_service.get_verification_count(did),
        "returned_count": len(records),
        "verifications": records
    }


@router.get("/global/stats")
async def get_global_stats():
    """
    Get global DID++ system statistics.
    
    Returns overall metrics from the blockchain:
    - Total DIDs registered
    - Total verifications
    - Network status
    """
    
    stats = blockchain_service.get_stats()
    
    return {
        "network": {
            "connected": stats['connected'],
            "configured": stats['configured'],
            "chain_id": stats['chain_id'],
            "chain_name": "Ethereum Sepolia Testnet"
        },
        "registry": {
            "total_dids": stats.get('total_dids', 0),
            "contract_address": config.DID_REGISTRY_ADDRESS
        },
        "verifications": {
            "total_verifications": stats.get('total_verifications', 0),
            "contract_address": config.VERIFICATION_LOG_ADDRESS
        },
        "wallet": {
            "address": stats.get('wallet_address', ''),
            "balance_eth": stats.get('wallet_balance_eth', 0)
        },
        "ipfs": {
            "configured": ipfs_service.is_configured(),
            "gateway": config.IPFS_GATEWAY
        },
        "explorer_urls": {
            "registry": config.get_address_url(config.DID_REGISTRY_ADDRESS) if config.DID_REGISTRY_ADDRESS else None,
            "verification_log": config.get_address_url(config.VERIFICATION_LOG_ADDRESS) if config.VERIFICATION_LOG_ADDRESS else None
        }
    }


@router.get("/events/recent")
async def get_recent_events(
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Get recent events across all DIDs.
    
    Returns the most recent registration and verification events
    from the blockchain.
    
    Args:
        limit: Maximum number of events to return
    """
    
    if not blockchain_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service not configured"
        )
    
    # Get recent registrations
    registrations = blockchain_service.get_registration_events()
    
    # Get recent verifications
    verifications = blockchain_service.get_verification_events()
    
    # Combine and sort by timestamp
    all_events = registrations + verifications
    all_events.sort(key=lambda x: (x['timestamp'], x['block_number']), reverse=True)
    
    # Take the most recent
    recent_events = all_events[:limit]
    
    # Format timestamps
    for event in recent_events:
        event['timestamp_formatted'] = format_timestamp(event['timestamp'])
    
    return {
        "total_events": len(all_events),
        "returned_count": len(recent_events),
        "events": recent_events
    }


@router.get("/ipfs/{cid}")
async def get_ipfs_metadata(cid: str):
    """
    Fetch and display IPFS metadata (without decryption).
    
    Returns the raw IPFS metadata structure. Embeddings remain
    encrypted and are not decrypted.
    
    Args:
        cid: IPFS Content Identifier
    """
    
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CID is required"
        )
    
    # Fetch from IPFS
    data, error = ipfs_service.fetch_metadata(cid)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch from IPFS: {error}"
        )
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found at CID: {cid}"
        )
    
    # Return metadata without decrypting embeddings
    # Mask the encrypted data for security
    safe_data = {
        "version": data.get('version'),
        "user_id": data.get('user_id'),
        "did": data.get('did'),
        "identity_hash": data.get('identity_hash'),
        "created_at": data.get('created_at'),
        "created_at_formatted": format_timestamp(data.get('created_at', 0)),
        "encryption_metadata": data.get('encryption_metadata'),
        "encrypted_data_present": {
            "face_embedding": bool(data.get('encrypted_face_embedding')),
            "voice_embedding": bool(data.get('encrypted_voice_embedding')),
            "doc_data": bool(data.get('encrypted_doc_data'))
        },
        "gateway_url": ipfs_service.get_gateway_url(cid)
    }
    
    return safe_data
