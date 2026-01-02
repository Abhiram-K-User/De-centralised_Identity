"""
DID++ Database Module
SQLite database connection and schema management.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from app.config import config


def init_database():
    """Initialize the database and create tables if they don't exist."""
    config.ensure_data_dir()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create users table for storing biometric data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                did TEXT UNIQUE NOT NULL,
                face_embedding BLOB,
                voice_embedding BLOB,
                doc_embedding BLOB,
                doc_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registration_tx_hash TEXT
            )
        """)
        
        # Create verifications table for logging verification attempts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                did TEXT NOT NULL,
                score REAL NOT NULL,
                face_score REAL,
                voice_score REAL,
                doc_score REAL,
                confidence_level TEXT,
                verified BOOLEAN NOT NULL,
                verification_tx_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (did) REFERENCES users(did)
            )
        """)
        
        conn.commit()


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_user(
    user_id: str,
    did: str,
    face_embedding: bytes,
    voice_embedding: bytes,
    doc_embedding: bytes,
    doc_text: str,
    registration_tx_hash: str
) -> bool:
    """Create a new user with encrypted embeddings."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (
                    user_id, did, face_embedding, voice_embedding, 
                    doc_embedding, doc_text, registration_tx_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, did, face_embedding, voice_embedding, 
                  doc_embedding, doc_text, registration_tx_hash))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def get_user_by_did(did: str) -> Optional[Dict[str, Any]]:
    """Retrieve user by DID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, did, face_embedding, voice_embedding, 
                   doc_embedding, doc_text, created_at, registration_tx_hash
            FROM users WHERE did = ?
        """, (did,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None


def get_user_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user by user_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, did, face_embedding, voice_embedding, 
                   doc_embedding, doc_text, created_at, registration_tx_hash
            FROM users WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None


def log_verification(
    did: str,
    score: float,
    face_score: float,
    voice_score: float,
    doc_score: float,
    confidence_level: str,
    verified: bool,
    verification_tx_hash: Optional[str] = None
) -> int:
    """Log a verification attempt."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO verifications (
                did, score, face_score, voice_score, doc_score,
                confidence_level, verified, verification_tx_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (did, score, face_score, voice_score, doc_score,
              confidence_level, verified, verification_tx_hash))
        conn.commit()
        return cursor.lastrowid


def get_verifications_by_did(did: str) -> list:
    """Get all verifications for a DID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, did, score, face_score, voice_score, doc_score,
                   confidence_level, verified, verification_tx_hash, created_at
            FROM verifications
            WHERE did = ?
            ORDER BY created_at DESC
        """, (did,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
