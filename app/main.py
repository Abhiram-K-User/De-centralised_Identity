"""
DID++ FastAPI Main Application
Fully decentralized biometric identity system.

Architecture:
- IPFS (Pinata): Encrypted biometric metadata storage
- Ethereum Sepolia: State management and immutable proofs
- No local database: All data is decentralized

Data Flow:
1. Registration: Biometrics → ML → Encrypt → IPFS → Blockchain
2. Verification: Blockchain → IPFS → Decrypt (in-memory) → Compare
3. History: Query blockchain event logs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import config
from app.routes import registration, verification, history, alias


# Initialize FastAPI app
app = FastAPI(
    title="DID++ Decentralized Biometric Identity System",
    description="""
    A fully decentralized multi-modal biometric identity system.
    
    ## Architecture
    - **IPFS**: Encrypted biometric metadata storage via Pinata
    - **Ethereum Sepolia**: Blockchain state management and verification proofs
    - **No Local Database**: All data is stored on decentralized infrastructure
    
    ## Data Flow
    - Registration: ~4MB biometrics → ~5KB encrypted IPFS → 32-byte blockchain hash
    - Verification: Blockchain CID lookup → IPFS fetch → In-memory decryption → Compare
    
    ## Smart Contracts
    - **DIDRegistry**: Maps DIDs to IPFS CIDs and identity hashes
    - **VerificationLog**: Immutable audit trail of verification events
    """,
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(registration.router, prefix="/api", tags=["Registration"])
app.include_router(verification.router, prefix="/api", tags=["Verification"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(alias.router, prefix="/api/alias", tags=["Alias Management"])


@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.
    
    Validates configuration for:
    - IPFS (Pinata)
    - Blockchain (Ethereum Sepolia)
    - Encryption (AES-256-CBC)
    """
    print("\n" + "=" * 60)
    print("DID++ Decentralized Identity System v2.0.0")
    print("=" * 60)
    
    # Check IPFS configuration
    if config.is_ipfs_configured():
        print("✓ IPFS (Pinata): Configured")
    else:
        print("✗ IPFS (Pinata): Not configured - set PINATA_JWT or PINATA_API_KEY/PINATA_SECRET_KEY")
    
    # Check blockchain configuration
    if config.is_blockchain_configured():
        from app.services.blockchain import blockchain_service
        if blockchain_service.is_connected():
            print("✓ Blockchain (Sepolia): Connected")
            stats = blockchain_service.get_stats()
            print(f"  - DIDRegistry: {config.DID_REGISTRY_ADDRESS}")
            print(f"  - VerificationLog: {config.VERIFICATION_LOG_ADDRESS}")
            print(f"  - Wallet: {stats.get('wallet_address', 'N/A')}")
            print(f"  - Balance: {stats.get('wallet_balance_eth', 0):.4f} ETH")
        else:
            print("✗ Blockchain (Sepolia): Not connected")
    else:
        print("✗ Blockchain (Sepolia): Not configured - set contract addresses and keys")
    
    # Check encryption configuration
    if config.is_encryption_configured():
        print("✓ Encryption (AES-256-CBC): Configured")
    else:
        print("✗ Encryption: Not configured - set MASTER_KEY (64 hex chars)")
    
    # Validate weights
    if config.validate_weights():
        print(f"✓ Biometric Weights: Face={config.FACE_WEIGHT}, Voice={config.VOICE_WEIGHT}, Doc={config.DOC_WEIGHT}")
    else:
        print("⚠ Biometric Weights: Do not sum to 1.0")
    
    print("=" * 60)
    print(f"API available at: http://{config.API_HOST}:{config.API_PORT}")
    print(f"Documentation at: http://{config.API_HOST}:{config.API_PORT}/api/docs")
    print("=" * 60 + "\n")


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns status of all decentralized services.
    """
    from app.services.blockchain import blockchain_service
    from app.services.ipfs import ipfs_service
    
    blockchain_connected = blockchain_service.is_connected()
    blockchain_configured = blockchain_service.is_configured()
    ipfs_configured = ipfs_service.is_configured()
    encryption_configured = config.is_encryption_configured()
    
    # Overall health
    is_healthy = ipfs_configured and encryption_configured
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "DID++ Decentralized Biometric Identity System",
        "version": "2.0.0",
        "architecture": "Fully Decentralized (IPFS + Blockchain)",
        "components": {
            "ipfs": {
                "status": "operational" if ipfs_configured else "not_configured",
                "provider": "Pinata",
                "gateway": config.IPFS_GATEWAY
            },
            "blockchain": {
                "status": "operational" if blockchain_connected else "not_connected",
                "configured": blockchain_configured,
                "network": "Ethereum Sepolia (Chain ID: 11155111)"
            },
            "encryption": {
                "status": "operational" if encryption_configured else "not_configured",
                "algorithm": "AES-256-CBC"
            },
            "database": {
                "status": "not_used",
                "note": "Fully decentralized - no local database"
            }
        },
        "data_reduction": {
            "pipeline": "~4MB raw → ~5KB IPFS → 32 bytes blockchain",
            "target_reduction": "~1600x total reduction"
        }
    }


@app.get("/api/config")
async def get_config():
    """
    Get public configuration (non-sensitive).
    
    Returns configuration that can be safely exposed to clients.
    """
    return {
        "version": "2.0.0",
        "network": {
            "chain_id": config.CHAIN_ID,
            "chain_name": "Ethereum Sepolia Testnet",
            "explorer": config.SEPOLIA_EXPLORER_URL
        },
        "contracts": {
            "did_registry": config.DID_REGISTRY_ADDRESS or "Not configured",
            "verification_log": config.VERIFICATION_LOG_ADDRESS or "Not configured"
        },
        "ipfs": {
            "gateway": config.IPFS_GATEWAY,
            "provider": "Pinata"
        },
        "verification": {
            "face_weight": config.FACE_WEIGHT,
            "voice_weight": config.VOICE_WEIGHT,
            "doc_weight": config.DOC_WEIGHT,
            "threshold": config.VERIFICATION_THRESHOLD
        },
        "embedding_dimensions": {
            "face": f"{config.FACE_EMBEDDING_DIM}-D (ArcFace)",
            "voice": f"{config.VOICE_EMBEDDING_DIM}-D (ECAPA-TDNN)",
            "document": f"{config.DOC_EMBEDDING_DIM}-D (Face+Text)"
        },
        "encryption": {
            "algorithm": "AES-256-CBC",
            "key_size": "256 bits",
            "iv_size": "128 bits (unique per session)",
            "padding": "PKCS7"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.API_LOG_LEVEL,
        reload=True
    )
