"""
DID++ Configuration Module
Loads environment variables and provides configuration settings for the
fully decentralized identity system using IPFS and Ethereum Sepolia.
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
    
    # ============ API Settings ============
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_LOG_LEVEL: str = os.getenv("API_LOG_LEVEL", "info")
    
    # ============ Blockchain (Ethereum Sepolia) ============
    # Smart contract addresses
    DID_REGISTRY_ADDRESS: str = os.getenv("DID_REGISTRY_ADDRESS", "")
    VERIFICATION_LOG_ADDRESS: str = os.getenv("VERIFICATION_LOG_ADDRESS", "")
    
    # Alchemy RPC
    ALCHEMY_KEY: str = os.getenv("ALCHEMY_KEY", "")
    
    # Wallet
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    
    # Chain settings
    CHAIN_ID: int = 11155111  # Sepolia testnet
    GAS_LIMIT: int = int(os.getenv("GAS_LIMIT", "300000"))
    
    # ============ IPFS (Pinata) ============
    PINATA_API_KEY: str = os.getenv("PINATA_API_KEY", "")
    PINATA_SECRET_KEY: str = os.getenv("PINATA_SECRET_KEY", "")
    PINATA_JWT: str = os.getenv("PINATA_JWT", "")  # Alternative to API key pair
    
    # IPFS Gateway
    IPFS_GATEWAY: str = os.getenv("IPFS_GATEWAY", "https://gateway.pinata.cloud/ipfs")
    
    # ============ Encryption ============
    # 32-byte (256-bit) master key as hex string
    MASTER_KEY: str = os.getenv("MASTER_KEY", "")
    
    # ============ Verification Settings ============
    # Biometric weights (must sum to 1.0)
    FACE_WEIGHT: float = float(os.getenv("FACE_WEIGHT", "0.40"))
    VOICE_WEIGHT: float = float(os.getenv("VOICE_WEIGHT", "0.35"))
    DOC_WEIGHT: float = float(os.getenv("DOC_WEIGHT", "0.25"))
    
    # Threshold for successful verification
    VERIFICATION_THRESHOLD: float = float(os.getenv("VERIFICATION_THRESHOLD", "0.75"))
    
    # ============ File Upload Settings ============
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # ============ Embedding Dimensions ============
    # ArcFace face embedding: 512-D
    FACE_EMBEDDING_DIM: int = 512
    # ECAPA-TDNN voice embedding: 192-D
    VOICE_EMBEDDING_DIM: int = 192
    # Document embedding: 512-D (face) + 128-D (text) = 640-D
    DOC_EMBEDDING_DIM: int = 640
    
    # ============ Data Reduction Target ============
    # Raw biometrics: ~4MB → Encrypted IPFS: ~5KB → Blockchain: 32 bytes
    TARGET_IPFS_SIZE_KB: int = 5
    BLOCKCHAIN_HASH_BYTES: int = 32
    
    @property
    def ALCHEMY_RPC_URL(self) -> str:
        """Get Alchemy RPC URL for Sepolia testnet."""
        return f"https://eth-sepolia.g.alchemy.com/v2/{self.ALCHEMY_KEY}"
    
    @property
    def SEPOLIA_EXPLORER_URL(self) -> str:
        """Get Etherscan URL for Sepolia."""
        return "https://sepolia.etherscan.io"
    
    def get_tx_url(self, tx_hash: str) -> str:
        """Get Etherscan URL for a transaction."""
        return f"{self.SEPOLIA_EXPLORER_URL}/tx/{tx_hash}"
    
    def get_address_url(self, address: str) -> str:
        """Get Etherscan URL for an address."""
        return f"{self.SEPOLIA_EXPLORER_URL}/address/{address}"
    
    def get_ipfs_url(self, cid: str) -> str:
        """Get IPFS gateway URL for a CID."""
        return f"{self.IPFS_GATEWAY}/{cid}"
    
    def is_blockchain_configured(self) -> bool:
        """Check if blockchain is properly configured."""
        return bool(
            self.DID_REGISTRY_ADDRESS and
            self.VERIFICATION_LOG_ADDRESS and
            self.ALCHEMY_KEY and
            self.PRIVATE_KEY
        )
    
    def is_ipfs_configured(self) -> bool:
        """Check if IPFS is properly configured."""
        return bool(
            self.PINATA_JWT or
            (self.PINATA_API_KEY and self.PINATA_SECRET_KEY)
        )
    
    def is_encryption_configured(self) -> bool:
        """Check if encryption is properly configured."""
        if not self.MASTER_KEY:
            return False
        try:
            key_bytes = bytes.fromhex(self.MASTER_KEY)
            return len(key_bytes) == 32
        except ValueError:
            return False
    
    def validate_weights(self) -> bool:
        """Validate that biometric weights sum to 1.0."""
        total = self.FACE_WEIGHT + self.VOICE_WEIGHT + self.DOC_WEIGHT
        return abs(total - 1.0) < 0.001


# Global config instance
config = Config()
