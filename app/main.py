"""
DID++ FastAPI Main Application
Entry point for the biometric decentralized identity system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import config
from app.database import init_database
from app.routes import registration, verification, history

# Initialize FastAPI app
app = FastAPI(
    title="DID++ Biometric Identity System",
    description="Multi-modal biometric decentralized identity system using Ethereum blockchain",
    version="1.0.0",
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


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_database()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "DID++ Biometric Identity System",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.API_LOG_LEVEL,
        reload=True
    )
