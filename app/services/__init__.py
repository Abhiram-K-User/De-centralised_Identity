"""
DID++ Services Package
Provides blockchain, encryption, IPFS, and ML services.
"""

from app.services.encryption import encryption_service, compute_sha256, compute_sha256_bytes
from app.services.blockchain_smart import blockchain_service  # Smart service with fallback
from app.services.ipfs import ipfs_service, create_ipfs_metadata

# Try to import ML engine (requires numpy)
try:
    import numpy as np
    from app.services.ml_engine import ml_engine
    ML_AVAILABLE = True
except ImportError:
    # Try mock ML engine
    try:
        from app.services.ml_engine_mock import ml_engine
        ML_AVAILABLE = True
    except ImportError:
        ml_engine = None
        ML_AVAILABLE = False

__all__ = [
    'encryption_service',
    'compute_sha256',
    'compute_sha256_bytes',
    'blockchain_service',  # Now uses SmartBlockchainService
    'ipfs_service',
    'create_ipfs_metadata',
    'ml_engine'
]
