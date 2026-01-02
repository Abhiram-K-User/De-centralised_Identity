"""
DID++ IPFS Service
Decentralized storage layer using Pinata for IPFS pinning.

Implements:
- Encrypted metadata upload to IPFS
- CID retrieval and content fetching
- Automatic garbage collection bypass via pinning
"""

import json
import httpx
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import hashlib
import time

from app.config import config


@dataclass
class IPFSUploadResult:
    """Result of an IPFS upload operation."""
    success: bool
    cid: str
    size_bytes: int
    pin_status: str
    gateway_url: str
    error: Optional[str] = None


@dataclass
class IPFSMetadata:
    """Encrypted biometric metadata structure for IPFS."""
    version: str
    user_id: str
    did: str
    encrypted_face_embedding: str  # Base64-encoded encrypted bytes
    encrypted_voice_embedding: str  # Base64-encoded encrypted bytes
    encrypted_doc_data: str  # Base64-encoded encrypted JSON (embedding + text)
    identity_hash: str  # Hex-encoded SHA-256 hash
    created_at: int  # Unix timestamp
    encryption_metadata: Dict[str, Any]  # IV and algorithm info (no key!)


class IPFSService:
    """
    IPFS service using Pinata for decentralized storage.
    
    Features:
    - Upload encrypted metadata JSON to IPFS
    - Pin content for persistence
    - Retrieve content by CID
    - Gateway URL generation for access
    """
    
    # Pinata API endpoints
    PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    PINATA_UNPIN_URL = "https://api.pinata.cloud/pinning/unpin"
    PINATA_PIN_LIST_URL = "https://api.pinata.cloud/data/pinList"
    
    # IPFS Gateway (Pinata dedicated gateway or public)
    IPFS_GATEWAY_URL = "https://gateway.pinata.cloud/ipfs"
    PUBLIC_GATEWAY_URL = "https://ipfs.io/ipfs"
    
    def __init__(
        self,
        pinata_api_key: str = None,
        pinata_secret_key: str = None,
        pinata_jwt: str = None
    ):
        """
        Initialize IPFS service with Pinata credentials.
        
        Args:
            pinata_api_key: Pinata API key
            pinata_secret_key: Pinata secret key
            pinata_jwt: Pinata JWT (alternative to API key pair)
        """
        self.api_key = pinata_api_key or config.PINATA_API_KEY
        self.secret_key = pinata_secret_key or config.PINATA_SECRET_KEY
        self.jwt = pinata_jwt or config.PINATA_JWT
        
        # Build headers based on available credentials
        self.headers = self._build_headers()
        
        # HTTP client with connection pooling
        self.client = httpx.Client(
            timeout=60.0,
            headers=self.headers
        )
    
    def _build_headers(self) -> Dict[str, str]:
        """Build authentication headers for Pinata API."""
        if self.jwt:
            return {
                "Authorization": f"Bearer {self.jwt}",
                "Content-Type": "application/json"
            }
        elif self.api_key and self.secret_key:
            return {
                "pinata_api_key": self.api_key,
                "pinata_secret_api_key": self.secret_key,
                "Content-Type": "application/json"
            }
        else:
            return {"Content-Type": "application/json"}
    
    def is_configured(self) -> bool:
        """Check if IPFS service is properly configured."""
        return bool(self.jwt or (self.api_key and self.secret_key))
    
    def upload_metadata(
        self,
        metadata: IPFSMetadata,
        pin_name: str = None
    ) -> IPFSUploadResult:
        """
        Upload encrypted biometric metadata to IPFS via Pinata.
        
        Args:
            metadata: IPFSMetadata object containing encrypted data
            pin_name: Optional name for the pin
            
        Returns:
            IPFSUploadResult with CID and upload status
        """
        if not self.is_configured():
            return IPFSUploadResult(
                success=False,
                cid="",
                size_bytes=0,
                pin_status="failed",
                gateway_url="",
                error="IPFS service not configured"
            )
        
        # Convert metadata to JSON-serializable dict
        metadata_dict = {
            "version": metadata.version,
            "user_id": metadata.user_id,
            "did": metadata.did,
            "encrypted_face_embedding": metadata.encrypted_face_embedding,
            "encrypted_voice_embedding": metadata.encrypted_voice_embedding,
            "encrypted_doc_data": metadata.encrypted_doc_data,
            "identity_hash": metadata.identity_hash,
            "created_at": metadata.created_at,
            "encryption_metadata": metadata.encryption_metadata
        }
        
        # Calculate size for stats
        json_str = json.dumps(metadata_dict)
        size_bytes = len(json_str.encode('utf-8'))
        
        # Prepare Pinata request
        pin_name = pin_name or f"did-metadata-{metadata.user_id}-{metadata.created_at}"
        
        payload = {
            "pinataContent": metadata_dict,
            "pinataMetadata": {
                "name": pin_name,
                "keyvalues": {
                    "did": metadata.did,
                    "user_id": metadata.user_id,
                    "type": "biometric_metadata",
                    "version": metadata.version
                }
            },
            "pinataOptions": {
                "cidVersion": 1  # Use CIDv1 for better compatibility
            }
        }
        
        try:
            response = self.client.post(
                self.PINATA_PIN_JSON_URL,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                cid = data.get("IpfsHash", "")
                
                return IPFSUploadResult(
                    success=True,
                    cid=cid,
                    size_bytes=size_bytes,
                    pin_status="pinned",
                    gateway_url=f"{self.IPFS_GATEWAY_URL}/{cid}"
                )
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    pass
                
                return IPFSUploadResult(
                    success=False,
                    cid="",
                    size_bytes=size_bytes,
                    pin_status="failed",
                    gateway_url="",
                    error=f"Pinata error: {error_msg}"
                )
                
        except Exception as e:
            return IPFSUploadResult(
                success=False,
                cid="",
                size_bytes=size_bytes,
                pin_status="failed",
                gateway_url="",
                error=f"Upload failed: {str(e)}"
            )
    
    def fetch_metadata(self, cid: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Fetch metadata from IPFS by CID.
        
        Args:
            cid: IPFS Content Identifier
            
        Returns:
            Tuple of (metadata_dict, error_message)
        """
        if not cid:
            return None, "CID is required"
        
        # Try Pinata gateway first, then public gateway
        gateways = [
            f"{self.IPFS_GATEWAY_URL}/{cid}",
            f"{self.PUBLIC_GATEWAY_URL}/{cid}"
        ]
        
        for gateway_url in gateways:
            try:
                response = self.client.get(
                    gateway_url,
                    headers={"Accept": "application/json"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json(), None
                    
            except Exception as e:
                continue
        
        return None, f"Failed to fetch CID: {cid}"
    
    def unpin(self, cid: str) -> bool:
        """
        Unpin content from Pinata (allows garbage collection).
        
        Args:
            cid: IPFS Content Identifier to unpin
            
        Returns:
            True if successful
        """
        if not self.is_configured() or not cid:
            return False
        
        try:
            response = self.client.delete(
                f"{self.PINATA_UNPIN_URL}/{cid}"
            )
            return response.status_code == 200
        except:
            return False
    
    def get_pin_status(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Get pinning status for a CID.
        
        Args:
            cid: IPFS Content Identifier
            
        Returns:
            Pin status info or None
        """
        if not self.is_configured() or not cid:
            return None
        
        try:
            response = self.client.get(
                self.PINATA_PIN_LIST_URL,
                params={"hashContains": cid, "status": "pinned"}
            )
            
            if response.status_code == 200:
                data = response.json()
                rows = data.get("rows", [])
                if rows:
                    return rows[0]
            return None
        except:
            return None
    
    def get_gateway_url(self, cid: str, use_public: bool = False) -> str:
        """
        Get gateway URL for a CID.
        
        Args:
            cid: IPFS Content Identifier
            use_public: Whether to use public gateway
            
        Returns:
            Gateway URL
        """
        if use_public:
            return f"{self.PUBLIC_GATEWAY_URL}/{cid}"
        return f"{self.IPFS_GATEWAY_URL}/{cid}"
    
    def calculate_data_reduction(
        self,
        raw_face_size: int,
        raw_voice_size: int,
        raw_doc_size: int,
        encrypted_metadata_size: int
    ) -> Dict[str, Any]:
        """
        Calculate data reduction statistics.
        
        Follows the 1600x data reduction pipeline:
        ~4MB raw biometrics → ~5KB encrypted metadata → 32-byte hash
        
        Args:
            raw_face_size: Size of raw face image in bytes
            raw_voice_size: Size of raw voice audio in bytes
            raw_doc_size: Size of raw document image in bytes
            encrypted_metadata_size: Size of encrypted metadata package
            
        Returns:
            Dictionary with reduction statistics
        """
        total_raw_size = raw_face_size + raw_voice_size + raw_doc_size
        hash_size = 32  # SHA-256 hash is 32 bytes
        
        # Calculate reduction ratios
        raw_to_encrypted_ratio = total_raw_size / encrypted_metadata_size if encrypted_metadata_size > 0 else 0
        raw_to_hash_ratio = total_raw_size / hash_size if hash_size > 0 else 0
        
        return {
            "raw_total_bytes": total_raw_size,
            "raw_total_kb": round(total_raw_size / 1024, 2),
            "raw_total_mb": round(total_raw_size / (1024 * 1024), 2),
            "encrypted_metadata_bytes": encrypted_metadata_size,
            "encrypted_metadata_kb": round(encrypted_metadata_size / 1024, 2),
            "blockchain_hash_bytes": hash_size,
            "reduction_raw_to_ipfs": f"{raw_to_encrypted_ratio:.0f}x",
            "reduction_raw_to_blockchain": f"{raw_to_hash_ratio:.0f}x",
            "storage_saved_percent": round((1 - encrypted_metadata_size / total_raw_size) * 100, 2) if total_raw_size > 0 else 0
        }
    
    def close(self):
        """Close HTTP client."""
        self.client.close()


# Helper function to create metadata object
def create_ipfs_metadata(
    user_id: str,
    did: str,
    encrypted_face: str,
    encrypted_voice: str,
    encrypted_doc: str,
    identity_hash: str,
    encryption_algorithm: str = "AES-256-CBC",
    version: str = "1.0.0"
) -> IPFSMetadata:
    """
    Create an IPFSMetadata object for upload.
    
    Args:
        user_id: Unique user identifier
        did: Decentralized Identifier
        encrypted_face: Base64-encoded encrypted face embedding
        encrypted_voice: Base64-encoded encrypted voice embedding
        encrypted_doc: Base64-encoded encrypted document data
        identity_hash: Hex-encoded SHA-256 hash
        encryption_algorithm: Encryption algorithm used
        version: Schema version
        
    Returns:
        IPFSMetadata object ready for upload
    """
    return IPFSMetadata(
        version=version,
        user_id=user_id,
        did=did,
        encrypted_face_embedding=encrypted_face,
        encrypted_voice_embedding=encrypted_voice,
        encrypted_doc_data=encrypted_doc,
        identity_hash=identity_hash,
        created_at=int(time.time()),
        encryption_metadata={
            "algorithm": encryption_algorithm,
            "key_derivation": "MASTER_KEY",
            "iv_included": True,
            "padding": "PKCS7"
        }
    )


# Global IPFS service instance
ipfs_service = IPFSService()

