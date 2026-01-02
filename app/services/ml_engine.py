"""
DID++ ML Engine
Multi-modal biometric processing for face, voice, and document embeddings.
Uses ArcFace for face recognition and SpeechBrain ECAPA-TDNN for speaker verification.
"""

import io
import os
import tempfile
import numpy as np
from typing import Tuple, Optional
import cv2
import librosa
import easyocr


class FaceProcessor:
    """
    Face embedding extraction using ArcFace (via InsightFace).
    Produces 512-D embeddings that are highly discriminative.
    """
    
    def __init__(self, output_dim: int = 512):
        self.output_dim = output_dim
        self.face_analyzer = None
        self._initialized = False
    
    def _get_analyzer(self):
        """Lazy initialization of InsightFace analyzer."""
        if not self._initialized:
            try:
                from insightface.app import FaceAnalysis
                
                # Initialize with ArcFace model
                self.face_analyzer = FaceAnalysis(
                    name='buffalo_l',  # Uses ArcFace model
                    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
                )
                self.face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
                self._initialized = True
            except Exception as e:
                print(f"Failed to initialize InsightFace: {e}")
                self._initialized = True  # Don't retry on failure
        return self.face_analyzer
    
    def process(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Process face image and return 512-D ArcFace embedding.
        
        Args:
            image_bytes: Raw image bytes (JPEG)
            
        Returns:
            512-D float32 embedding or None if face not detected
        """
        try:
            # Decode image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                print("Failed to decode image")
                return None
            
            # Get analyzer
            analyzer = self._get_analyzer()
            if analyzer is None:
                print("Face analyzer not initialized")
                return None
            
            # Detect faces and get embeddings
            faces = analyzer.get(image)
            
            if not faces or len(faces) == 0:
                print("No face detected in image")
                return None
            
            # Get embedding from the first (largest) face
            embedding = faces[0].embedding
            
            # Ensure it's float32 and normalized
            embedding = embedding.astype(np.float32)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            print(f"Face processing error: {e}")
            import traceback
            traceback.print_exc()
            return None


class VoiceProcessor:
    """
    Voice embedding extraction using SpeechBrain ECAPA-TDNN.
    Produces 192-D speaker embeddings that are highly discriminative.
    """
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.encoder = None
        self._initialized = False
    
    def _get_encoder(self):
        """Lazy initialization of SpeechBrain speaker encoder."""
        if not self._initialized:
            try:
                from speechbrain.pretrained import EncoderClassifier
                import torch
                
                # Use ECAPA-TDNN model for speaker embedding
                self.encoder = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="data/speechbrain_models/spkrec-ecapa-voxceleb",
                    run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"}
                )
                self._initialized = True
                print("SpeechBrain ECAPA-TDNN model loaded successfully")
            except Exception as e:
                print(f"Failed to initialize SpeechBrain: {e}")
                import traceback
                traceback.print_exc()
                self._initialized = True  # Don't retry on failure
        return self.encoder
    
    def process(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """
        Process voice audio and return 192-D speaker embedding.
        
        Args:
            audio_bytes: Raw audio bytes (WAV/WebM format)
            
        Returns:
            192-D float32 embedding or None on error
        """
        try:
            # Load audio using librosa (handles various formats)
            audio_io = io.BytesIO(audio_bytes)
            y, sr = librosa.load(audio_io, sr=self.sample_rate)
            
            if len(y) == 0:
                print("Empty audio")
                return None
            
            # Minimum 1 second of audio
            if len(y) < self.sample_rate:
                # Pad with silence if too short
                y = np.pad(y, (0, self.sample_rate - len(y)))
            
            # Get encoder
            encoder = self._get_encoder()
            if encoder is None:
                print("Voice encoder not initialized, falling back to MFCC")
                return self._fallback_mfcc(y, sr)
            
            import torch
            
            # Convert to tensor (SpeechBrain expects [batch, time])
            audio_tensor = torch.tensor(y).unsqueeze(0).float()
            
            # Get embedding
            with torch.no_grad():
                embedding = encoder.encode_batch(audio_tensor)
                embedding = embedding.squeeze().cpu().numpy()
            
            # Ensure it's float32 and normalized
            embedding = embedding.astype(np.float32)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            print(f"Voice processing error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to MFCC
            try:
                audio_io = io.BytesIO(audio_bytes)
                y, sr = librosa.load(audio_io, sr=self.sample_rate)
                return self._fallback_mfcc(y, sr)
            except:
                return None
    
    def _fallback_mfcc(self, y: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """Fallback MFCC embedding if SpeechBrain fails."""
        try:
            # Extract MFCCs
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
            
            # Compute statistics
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)
            mfcc_delta = np.mean(librosa.feature.delta(mfccs), axis=1)
            mfcc_delta2 = np.mean(librosa.feature.delta(mfccs, order=2), axis=1)
            
            # Concatenate features (40*4 = 160, pad to 192)
            embedding = np.concatenate([mfcc_mean, mfcc_std, mfcc_delta, mfcc_delta2])
            
            # Pad to 192 dimensions to match ECAPA-TDNN
            if len(embedding) < 192:
                embedding = np.pad(embedding, (0, 192 - len(embedding)))
            else:
                embedding = embedding[:192]
            
            # L2 normalize
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding.astype(np.float32)
        except Exception as e:
            print(f"MFCC fallback error: {e}")
            return None


class DocumentProcessor:
    """
    Document processing using EasyOCR and ArcFace.
    Extracts text and face embedding for combined embedding.
    """
    
    def __init__(self, output_dim: int = 512):
        self.output_dim = output_dim
        
        # Initialize EasyOCR reader with GPU support
        self.reader = easyocr.Reader(['en'], gpu=True)
        
        # Initialize face processor for document face detection
        self.face_processor = FaceProcessor()
        
        # Text embedding dimension
        self.text_dim = 128
    
    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from document using OCR."""
        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return ""
        
        # Run OCR
        results = self.reader.readtext(image)
        
        # Combine all detected text
        text_parts = [result[1] for result in results]
        return " ".join(text_parts)
    
    def text_to_embedding(self, text: str) -> np.ndarray:
        """
        Convert text to a simple embedding using character-level features.
        """
        if not text:
            return np.zeros(self.text_dim, dtype=np.float32)
        
        # Character frequency features
        text_lower = text.lower()
        char_freq = np.zeros(26 + 10, dtype=np.float32)  # a-z + 0-9
        
        for char in text_lower:
            if 'a' <= char <= 'z':
                char_freq[ord(char) - ord('a')] += 1
            elif '0' <= char <= '9':
                char_freq[26 + int(char)] += 1
        
        # Normalize
        if char_freq.sum() > 0:
            char_freq = char_freq / char_freq.sum()
        
        # Expand to text_dim using projection
        np.random.seed(43)
        projection = np.random.randn(36, self.text_dim).astype(np.float32)
        embedding = np.dot(char_freq, projection)
        
        # L2 normalize
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding.astype(np.float32)
    
    def process(self, image_bytes: bytes) -> Tuple[Optional[np.ndarray], str]:
        """
        Process document and return embedding and extracted text.
        
        Args:
            image_bytes: Raw image bytes (JPEG)
            
        Returns:
            Tuple of (embedding, extracted text)
        """
        # Extract text
        text = self.extract_text(image_bytes)
        
        # Extract face from document using ArcFace
        face_embedding = self.face_processor.process(image_bytes)
        
        # Create text embedding
        text_embedding = self.text_to_embedding(text)
        
        if face_embedding is not None:
            # Combine face (512D) and text (128D) embeddings
            combined = np.concatenate([face_embedding, text_embedding])
        else:
            # Use text only, pad with zeros for face portion
            combined = np.concatenate([
                np.zeros(512, dtype=np.float32),
                text_embedding
            ])
        
        # L2 normalize final embedding
        combined = combined / (np.linalg.norm(combined) + 1e-8)
        
        return combined.astype(np.float32), text


class MLEngine:
    """Main ML engine combining all biometric processors."""
    
    def __init__(self):
        self.face_processor = FaceProcessor()
        self.voice_processor = VoiceProcessor()
        self.document_processor = DocumentProcessor()
    
    def process_face(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Process face image and return 512-D ArcFace embedding."""
        return self.face_processor.process(image_bytes)
    
    def process_voice(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """Process voice audio and return 192-D speaker embedding."""
        return self.voice_processor.process(audio_bytes)
    
    def process_document(self, image_bytes: bytes) -> Tuple[Optional[np.ndarray], str]:
        """Process document and return embedding + text."""
        return self.document_processor.process(image_bytes)
    
    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        # Handle different embedding sizes
        if len(a) != len(b):
            min_len = min(len(a), len(b))
            a = a[:min_len]
            b = b[:min_len]
        
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot / (norm_a * norm_b))
    
    @staticmethod
    def text_overlap(text1: str, text2: str) -> float:
        """
        Compute text overlap score using Jaccard similarity.
        """
        if not text1 or not text2:
            return 0.0
        
        # Tokenize (simple whitespace split)
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)


# Global ML engine instance
ml_engine = MLEngine()
