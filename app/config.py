"""
DID++ Configuration Module
Loads environment variables and provides configuration settings.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration settings."""
    
    # Database
    DB_PATH: str = os.getenv("DB_PATH", "data/biometrics.db")
    
    # API Settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_LOG_LEVEL: str = os.getenv("API_LOG_LEVEL", "info")
    
    # Blockchain
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    ALCHEMY_KEY: str = os.getenv("ALCHEMY_KEY", "")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    
    # Encryption
    MASTER_KEY: str = os.getenv("MASTER_KEY", "")
    
    # Verification Weights
    FACE_WEIGHT: float = float(os.getenv("FACE_WEIGHT", "0.40"))
    VOICE_WEIGHT: float = float(os.getenv("VOICE_WEIGHT", "0.35"))
    DOC_WEIGHT: float = float(os.getenv("DOC_WEIGHT", "0.25"))
    VERIFICATION_THRESHOLD: float = float(os.getenv("VERIFICATION_THRESHOLD", "0.75"))
    
    # File Upload Limits
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Embedding Dimensions
    FACE_EMBEDDING_DIM: int = 256
    VOICE_EMBEDDING_DIM: int = 80
    DOC_EMBEDDING_DIM: int = 256
    
    @property
    def ALCHEMY_RPC_URL(self) -> str:
        """Get Alchemy RPC URL for Sepolia testnet."""
        return f"https://eth-sepolia.g.alchemy.com/v2/{self.ALCHEMY_KEY}"
    
    def ensure_data_dir(self):
        """Ensure the data directory exists."""
        db_path = Path(self.DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()
