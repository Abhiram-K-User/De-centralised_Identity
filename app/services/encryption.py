"""
DID++ Encryption Service
AES-256-CBC encryption for securing biometric embeddings.
"""

import os
import base64
import hashlib
from typing import Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

from app.config import config


class EncryptionService:
    """AES-256-CBC encryption service for biometric embeddings."""
    
    def __init__(self, master_key: str = None):
        """
        Initialize encryption service.
        
        Args:
            master_key: Hex-encoded 32-byte master key (256 bits)
        """
        key_hex = master_key or config.MASTER_KEY
        if not key_hex:
            raise ValueError("Master key not configured")
        
        # Convert hex string to bytes (32 bytes = 256 bits)
        self.key = bytes.fromhex(key_hex)
        if len(self.key) != 32:
            raise ValueError("Master key must be 32 bytes (256 bits)")
    
    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt data using AES-256-CBC.
        
        Args:
            data: Raw bytes to encrypt
            
        Returns:
            Base64-encoded ciphertext (IV + encrypted data)
        """
        # Generate random 16-byte IV
        iv = os.urandom(16)
        
        # Apply PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Create cipher and encrypt
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and ciphertext, then Base64 encode
        combined = iv + ciphertext
        return base64.b64encode(combined)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data using AES-256-CBC.
        
        Args:
            encrypted_data: Base64-encoded ciphertext (IV + encrypted data)
            
        Returns:
            Decrypted raw bytes
        """
        # Base64 decode
        combined = base64.b64decode(encrypted_data)
        
        # Extract IV (first 16 bytes) and ciphertext
        iv = combined[:16]
        ciphertext = combined[16:]
        
        # Create cipher and decrypt
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    
    def encrypt_embedding(self, embedding: bytes) -> bytes:
        """Encrypt a biometric embedding."""
        return self.encrypt(embedding)
    
    def decrypt_embedding(self, encrypted_embedding: bytes) -> bytes:
        """Decrypt a biometric embedding."""
        return self.decrypt(encrypted_embedding)


# Global encryption service instance
encryption_service = EncryptionService()


def compute_sha256(data: Union[bytes, str]) -> str:
    """Compute SHA256 hash of data."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def compute_sha256_bytes(data: Union[bytes, str]) -> bytes:
    """Compute SHA256 hash of data as bytes."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).digest()
