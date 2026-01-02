"""
DID++ Alias Management API
Manage short codes and custom aliases for DIDs.

Features:
- View short code and aliases for a DID
- Register custom aliases
- Remove custom aliases
- Check alias availability
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.alias import alias_service
from app.services.blockchain import blockchain_service


router = APIRouter()


class AliasInfo(BaseModel):
    """Alias information for a DID."""
    did: str
    short_code: str
    aliases: List[str]


class RegisterAliasRequest(BaseModel):
    """Request to register a custom alias."""
    did: str = Field(..., description="Full DID to associate with alias")
    alias: str = Field(..., min_length=3, max_length=20, description="Custom alias (3-20 chars)")


class RegisterAliasResponse(BaseModel):
    """Response for alias registration."""
    success: bool
    did: str
    alias: str
    short_code: str
    message: str


class RemoveAliasRequest(BaseModel):
    """Request to remove a custom alias."""
    did: str = Field(..., description="Full DID that owns the alias")
    alias: str = Field(..., description="Alias to remove")


class ResolveResponse(BaseModel):
    """Response for identifier resolution."""
    identifier: str
    resolved_did: Optional[str]
    short_code: Optional[str]
    aliases: List[str]
    found: bool


@router.get("/info/{identifier}", response_model=AliasInfo)
async def get_alias_info(identifier: str):
    """
    Get alias information for a DID.
    
    Accepts:
    - Full DID
    - Short code
    - Custom alias
    
    Returns the DID along with its short code and all registered aliases.
    """
    
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
    
    # Get identifiers
    identifiers = alias_service.get_identifiers(did)
    
    return AliasInfo(
        did=did,
        short_code=identifiers['short_code'],
        aliases=identifiers['aliases']
    )


@router.post("/register", response_model=RegisterAliasResponse)
async def register_alias(request: RegisterAliasRequest):
    """
    Register a custom alias for a DID.
    
    Requirements:
    - Alias must be 3-20 characters
    - Must start with a letter
    - Can contain letters, numbers, underscores, and hyphens
    - Must be unique (not already taken)
    - DID must exist on the blockchain
    
    Args:
        request: Contains DID and desired alias
    """
    
    did = request.did
    alias = request.alias
    
    # Verify DID exists on blockchain (optional - for extra security)
    if blockchain_service.is_configured():
        exists, _ = blockchain_service.is_did_active(did)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DID not found on blockchain: {did}"
            )
    
    # Try to register the alias
    success, error = alias_service.register_alias(alias, did)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Get current identifiers
    identifiers = alias_service.get_identifiers(did)
    
    return RegisterAliasResponse(
        success=True,
        did=did,
        alias=alias.lower(),
        short_code=identifiers['short_code'],
        message=f"Alias '{alias}' registered successfully! You can now use it instead of your DID."
    )


@router.delete("/remove")
async def remove_alias(request: RemoveAliasRequest):
    """
    Remove a custom alias for a DID.
    
    Note: Auto-generated short codes cannot be removed.
    
    Args:
        request: Contains DID and alias to remove
    """
    
    success, error = alias_service.remove_alias(request.alias, request.did)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {
        "success": True,
        "did": request.did,
        "removed_alias": request.alias,
        "message": f"Alias '{request.alias}' removed successfully"
    }


@router.get("/resolve/{identifier}", response_model=ResolveResponse)
async def resolve_identifier(identifier: str):
    """
    Resolve an identifier to its full DID.
    
    Accepts:
    - Full DID (returned as-is)
    - Short code (8 characters)
    - Custom alias
    
    Returns the resolved DID and all associated identifiers.
    """
    
    # Try to resolve
    did = alias_service.resolve(identifier)
    
    if did:
        identifiers = alias_service.get_identifiers(did)
        return ResolveResponse(
            identifier=identifier,
            resolved_did=did,
            short_code=identifiers['short_code'],
            aliases=identifiers['aliases'],
            found=True
        )
    elif identifier.startswith("did:"):
        # It's a DID that might not be in the alias cache
        identifiers = alias_service.get_identifiers(identifier)
        return ResolveResponse(
            identifier=identifier,
            resolved_did=identifier,
            short_code=identifiers['short_code'],
            aliases=identifiers['aliases'],
            found=True
        )
    else:
        return ResolveResponse(
            identifier=identifier,
            resolved_did=None,
            short_code=None,
            aliases=[],
            found=False
        )


@router.get("/available/{alias}")
async def check_availability(alias: str):
    """
    Check if an alias is available for registration.
    
    Args:
        alias: Proposed alias to check
    """
    
    available = alias_service.is_available(alias)
    
    # Also validate the format
    from app.services.alias import validate_alias
    is_valid, error = validate_alias(alias)
    
    return {
        "alias": alias,
        "available": available and is_valid,
        "valid_format": is_valid,
        "format_error": error if not is_valid else None,
        "message": "Alias is available!" if (available and is_valid) else (error if not is_valid else "Alias is already taken")
    }


@router.get("/generate-preview")
async def generate_preview(did: str):
    """
    Preview the short code that would be generated for a DID.
    
    This is useful before registration to show users their short code.
    
    Args:
        did: Full DID to generate short code for
    """
    
    short_code = alias_service.generate_short_code(did)
    
    return {
        "did": did,
        "short_code": short_code,
        "message": f"Your short code will be: {short_code}"
    }

