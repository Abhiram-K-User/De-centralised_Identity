"""
DID++ Simple Smart Blockchain Service
A straightforward service selector with basic fallback for college project.

Simple Strategy:
1. Try optimized service (if enabled)
2. If it fails, use legacy service
3. Log when fallback happens
"""

import logging
from typing import Optional, Any, Tuple, List, Dict

logger = logging.getLogger(__name__)


class SimpleSmartBlockchainService:
    """
    Simple blockchain service with basic fallback.
    
    - Uses optimized service if USE_OPTIMIZED_BLOCKCHAIN=true
    - Falls back to legacy service on any error
    - Logs fallback events for debugging
    """
    
    def __init__(self):
        # Check if we should use optimized
        import os
        self.use_optimized = os.getenv("USE_OPTIMIZED_BLOCKCHAIN", "false").lower() == "true"
        
        # Load services
        self.optimized_service = None
        self.legacy_service = None
        
        # Try to load optimized service
        if self.use_optimized:
            try:
                from app.services.blockchain_optimized import BlockchainServiceOptimized
                self.optimized_service = BlockchainServiceOptimized()
                logger.info("[+] Using optimized blockchain service")
            except Exception as e:
                logger.warning(f"[!] Could not load optimized service: {e}")
                self.use_optimized = False
        
        # Always load legacy service (our safety net)
        from app.services.blockchain import BlockchainService
        self.legacy_service = BlockchainService()
        
        if not self.use_optimized:
            logger.info("📌 Using legacy blockchain service")
        
        # Simple counter
        self.fallback_count = 0
    
    def get_service_name(self) -> str:
        """Return the name of the currently active service."""
        if self.use_optimized and self.optimized_service:
            return "optimized"
        return "legacy"
    
    def _call_with_fallback(self, method_name: str, *args, **kwargs) -> Any:
        """
        Call method with simple fallback logic.
        
        Args:
            method_name: Method to call
            *args, **kwargs: Method arguments
            
        Returns:
            Result from optimized or legacy service
        """
        # If optimized not enabled, use legacy
        if not self.use_optimized or not self.optimized_service:
            method = getattr(self.legacy_service, method_name)
            return method(*args, **kwargs)
        
        # Try optimized first
        try:
            method = getattr(self.optimized_service, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            # Any error - fallback to legacy
            self.fallback_count += 1
            logger.warning(f"[!] Optimized service failed for {method_name}, using legacy")
            logger.warning(f"   Error: {e}")
            
            # Use legacy
            method = getattr(self.legacy_service, method_name)
            return method(*args, **kwargs)
    
    # ============ All blockchain methods ============
    
    def register_did(self, did: str, metadata_cid: str, identity_hash: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Register DID."""
        return self._call_with_fallback('register_did', did, metadata_cid, identity_hash)
    
    def update_did(self, did: str, new_metadata_cid: str, new_identity_hash: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Update DID."""
        return self._call_with_fallback('update_did', did, new_metadata_cid, new_identity_hash)
    
    def get_metadata_cid(self, did: str) -> Tuple[Optional[str], Optional[str]]:
        """Get CID."""
        return self._call_with_fallback('get_metadata_cid', did)
    
    def get_did_record(self, did: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Get DID record."""
        return self._call_with_fallback('get_did_record', did)
    
    def is_did_active(self, did: str) -> Tuple[bool, bool]:
        """Check if DID is active."""
        return self._call_with_fallback('is_did_active', did)
    
    def log_verification(self, did: str, verification_hash: bytes, metadata_cid: str, 
                        confidence_level: str, success: bool) -> Tuple[Optional[str], Optional[str]]:
        """Log verification."""
        return self._call_with_fallback('log_verification', did, verification_hash, 
                                       metadata_cid, confidence_level, success)
    
    def get_verification_count(self, did: str) -> int:
        """Get verification count."""
        return self._call_with_fallback('get_verification_count', did)
    
    def get_recent_verifications(self, did: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent verifications."""
        return self._call_with_fallback('get_recent_verifications', did, limit)
    
    def get_registration_events(self, did: str = None, from_block: int = 0) -> List[Dict[str, Any]]:
        """Get registration events."""
        return self._call_with_fallback('get_registration_events', did, from_block)
    
    def get_verification_events(self, did: str = None, from_block: int = 0) -> List[Dict[str, Any]]:
        """Get verification events."""
        return self._call_with_fallback('get_verification_events', did, from_block)
    
    def get_full_timeline(self, did: str) -> List[Dict[str, Any]]:
        """Get full timeline."""
        return self._call_with_fallback('get_full_timeline', did)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stats."""
        return self._call_with_fallback('get_stats')
    
    def is_connected(self) -> bool:
        """Check connection."""
        return self._call_with_fallback('is_connected')
    
    def is_configured(self) -> bool:
        """Check configuration."""
        return self._call_with_fallback('is_configured')
    
    # ============ Simple metrics ============
    
    def get_fallback_count(self) -> int:
        """Get number of times we fell back to legacy."""
        return self.fallback_count
    
    def get_service_name(self) -> str:
        """Get current service name."""
        if self.use_optimized and self.optimized_service:
            return "optimized"
        return "legacy"


# Global service instance
blockchain_service = SimpleSmartBlockchainService()
