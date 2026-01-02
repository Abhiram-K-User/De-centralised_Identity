"""
DID++ Alias Service
Provides user-friendly short codes and custom aliases for DIDs.

Features:
- Auto-generated 8-character short codes from DIDs
- Custom user-defined aliases (3-20 characters)
- Bidirectional lookup (alias → DID and DID → alias)
- Local JSON storage for quick lookups
"""

import json
import hashlib
import base64
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from app.config import config


# Alias storage file
ALIAS_FILE = Path("data/aliases.json")


def generate_short_code(did: str) -> str:
    """
    Generate an 8-character short code from a DID.
    
    The short code is:
    - Deterministic (same DID always produces same code)
    - URL-safe (lowercase alphanumeric)
    - Easy to type and remember
    
    Args:
        did: Full DID string
        
    Returns:
        8-character short code (e.g., "mzxw6ytb")
    """
    # Hash the DID
    hash_bytes = hashlib.sha256(did.encode()).digest()
    
    # Take first 6 bytes and encode as base32
    # Base32 uses A-Z and 2-7, which is readable and unambiguous
    encoded = base64.b32encode(hash_bytes[:6]).decode().lower()
    
    # Remove padding and take first 8 chars
    short_code = encoded.rstrip('=')[:8]
    
    return short_code


def validate_alias(alias: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a custom alias.
    
    Rules:
    - 3-20 characters long
    - Alphanumeric, underscores, and hyphens only
    - Cannot start with a number
    - Cannot be a reserved word
    
    Args:
        alias: Proposed alias string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not alias:
        return False, "Alias cannot be empty"
    
    if len(alias) < 3:
        return False, "Alias must be at least 3 characters"
    
    if len(alias) > 20:
        return False, "Alias must be 20 characters or less"
    
    # Check format: alphanumeric, underscores, hyphens
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', alias):
        return False, "Alias must start with a letter and contain only letters, numbers, underscores, and hyphens"
    
    # Reserved words
    reserved = {'admin', 'system', 'root', 'api', 'did', 'user', 'null', 'undefined'}
    if alias.lower() in reserved:
        return False, f"'{alias}' is a reserved word"
    
    return True, None


def _load_aliases() -> Dict:
    """Load aliases from storage file."""
    if not ALIAS_FILE.exists():
        return {
            "aliases": {},      # alias/short_code → DID
            "reverse": {},      # DID → {short_code, aliases: []}
            "metadata": {}      # alias → {created_at, type}
        }
    
    try:
        return json.loads(ALIAS_FILE.read_text())
    except (json.JSONDecodeError, Exception):
        return {
            "aliases": {},
            "reverse": {},
            "metadata": {}
        }


def _save_aliases(data: Dict) -> None:
    """Save aliases to storage file."""
    ALIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALIAS_FILE.write_text(json.dumps(data, indent=2))


def register_short_code(did: str) -> str:
    """
    Register the auto-generated short code for a DID.
    
    Called automatically during registration.
    
    Args:
        did: Full DID string
        
    Returns:
        The 8-character short code
    """
    short_code = generate_short_code(did)
    
    data = _load_aliases()
    
    # Store short code → DID mapping
    data["aliases"][short_code] = did
    
    # Store reverse mapping
    if did not in data["reverse"]:
        data["reverse"][did] = {
            "short_code": short_code,
            "aliases": []
        }
    else:
        data["reverse"][did]["short_code"] = short_code
    
    # Store metadata
    data["metadata"][short_code] = {
        "type": "short_code",
        "created_at": datetime.utcnow().isoformat(),
        "did": did
    }
    
    _save_aliases(data)
    
    return short_code


def register_alias(alias: str, did: str) -> Tuple[bool, Optional[str]]:
    """
    Register a custom alias for a DID.
    
    Args:
        alias: Custom alias (3-20 characters)
        did: Full DID string
        
    Returns:
        Tuple of (success, error_message)
    """
    # Validate alias format
    is_valid, error = validate_alias(alias)
    if not is_valid:
        return False, error
    
    alias_lower = alias.lower()
    
    data = _load_aliases()
    
    # Check if alias already exists
    if alias_lower in data["aliases"]:
        existing_did = data["aliases"][alias_lower]
        if existing_did != did:
            return False, f"Alias '{alias}' is already taken"
        else:
            return True, None  # Already registered to this DID
    
    # Check if it conflicts with a short code
    if alias_lower in data["aliases"]:
        return False, f"'{alias}' conflicts with an existing identifier"
    
    # Store alias → DID mapping
    data["aliases"][alias_lower] = did
    
    # Update reverse mapping
    if did not in data["reverse"]:
        # Generate short code if not exists
        short_code = generate_short_code(did)
        data["reverse"][did] = {
            "short_code": short_code,
            "aliases": [alias_lower]
        }
        data["aliases"][short_code] = did
    else:
        if alias_lower not in data["reverse"][did]["aliases"]:
            data["reverse"][did]["aliases"].append(alias_lower)
    
    # Store metadata
    data["metadata"][alias_lower] = {
        "type": "custom_alias",
        "created_at": datetime.utcnow().isoformat(),
        "did": did,
        "original_case": alias
    }
    
    _save_aliases(data)
    
    return True, None


def resolve(identifier: str) -> Optional[str]:
    """
    Resolve an identifier (alias, short code, or DID) to a full DID.
    
    This is the main lookup function used during verification.
    
    Args:
        identifier: Could be:
            - Full DID (did:eth:sepolia:...)
            - Short code (8 chars)
            - Custom alias
            
    Returns:
        Full DID string or None if not found
    """
    if not identifier:
        return None
    
    # If it's already a full DID, return it
    if identifier.startswith("did:"):
        return identifier
    
    # Try to resolve as alias or short code
    identifier_lower = identifier.lower()
    
    data = _load_aliases()
    
    if identifier_lower in data["aliases"]:
        return data["aliases"][identifier_lower]
    
    return None


def get_identifiers(did: str) -> Dict:
    """
    Get all identifiers (short code and aliases) for a DID.
    
    Args:
        did: Full DID string
        
    Returns:
        Dict with short_code and aliases list
    """
    data = _load_aliases()
    
    if did in data["reverse"]:
        return data["reverse"][did]
    
    # Generate short code if not registered yet
    short_code = generate_short_code(did)
    return {
        "short_code": short_code,
        "aliases": []
    }


def remove_alias(alias: str, did: str) -> Tuple[bool, Optional[str]]:
    """
    Remove a custom alias for a DID.
    
    Note: Short codes cannot be removed.
    
    Args:
        alias: The alias to remove
        did: The DID that owns this alias
        
    Returns:
        Tuple of (success, error_message)
    """
    alias_lower = alias.lower()
    
    data = _load_aliases()
    
    # Check if alias exists
    if alias_lower not in data["aliases"]:
        return False, f"Alias '{alias}' not found"
    
    # Check ownership
    if data["aliases"][alias_lower] != did:
        return False, "Not authorized to remove this alias"
    
    # Check if it's a short code (can't remove)
    if alias_lower in data["metadata"]:
        if data["metadata"][alias_lower].get("type") == "short_code":
            return False, "Cannot remove auto-generated short codes"
    
    # Remove from aliases
    del data["aliases"][alias_lower]
    
    # Remove from reverse mapping
    if did in data["reverse"]:
        if alias_lower in data["reverse"][did]["aliases"]:
            data["reverse"][did]["aliases"].remove(alias_lower)
    
    # Remove metadata
    if alias_lower in data["metadata"]:
        del data["metadata"][alias_lower]
    
    _save_aliases(data)
    
    return True, None


def list_all_aliases() -> List[Dict]:
    """
    List all registered aliases and short codes.
    
    Returns:
        List of alias info dicts
    """
    data = _load_aliases()
    
    result = []
    for identifier, did in data["aliases"].items():
        meta = data["metadata"].get(identifier, {})
        result.append({
            "identifier": identifier,
            "did": did,
            "type": meta.get("type", "unknown"),
            "created_at": meta.get("created_at")
        })
    
    return result


def is_alias_available(alias: str) -> bool:
    """
    Check if an alias is available for registration.
    
    Args:
        alias: Proposed alias
        
    Returns:
        True if available
    """
    # Validate format first
    is_valid, _ = validate_alias(alias)
    if not is_valid:
        return False
    
    data = _load_aliases()
    return alias.lower() not in data["aliases"]


# Convenience function for the service layer
class AliasService:
    """Service class for alias operations."""
    
    @staticmethod
    def generate_short_code(did: str) -> str:
        return generate_short_code(did)
    
    @staticmethod
    def register_short_code(did: str) -> str:
        return register_short_code(did)
    
    @staticmethod
    def register_alias(alias: str, did: str) -> Tuple[bool, Optional[str]]:
        return register_alias(alias, did)
    
    @staticmethod
    def resolve(identifier: str) -> Optional[str]:
        return resolve(identifier)
    
    @staticmethod
    def get_identifiers(did: str) -> Dict:
        return get_identifiers(did)
    
    @staticmethod
    def remove_alias(alias: str, did: str) -> Tuple[bool, Optional[str]]:
        return remove_alias(alias, did)
    
    @staticmethod
    def is_available(alias: str) -> bool:
        return is_alias_available(alias)


# Global service instance
alias_service = AliasService()

