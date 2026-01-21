"""
DID++ ML Engine
Multi-modal biometric processing for face, voice, and document embeddings.
Uses FaceNet (InceptionResnetV1) for face recognition and SpeechBrain ECAPA-TDNN for speaker verification.
"""

import os

os.environ['SPEECHBRAIN_LOCAL_STRATEGY'] = 'copy'

import io
import tempfile
import numpy as np
from typing import Tuple, Optional
import cv2
import librosa
import easyocr


class FaceProcessor:
    """
    Face embedding extraction using FaceNet (via facenet-pytorch).
    Produces 512-D embeddings that are highly discriminative.
    Uses MTCNN for face detection and InceptionResnetV1 pretrained on VGGFace2.
    """
    
    def __init__(self, output_dim: int = 512):
        self.output_dim = output_dim
        self.mtcnn = None
        self.resnet = None
        self._initialized = False
        self._device = None
    
    def _get_models(self):
        """Lazy initialization of FaceNet models with GPU support."""
        if not self._initialized:
            try:
                import torch
                from facenet_pytorch import MTCNN, InceptionResnetV1
                
                # Diagnostic logging for GPU availability
                cuda_available = torch.cuda.is_available()
                print(f"PyTorch version: {torch.__version__}")
                print(f"CUDA available: {cuda_available}")
                if cuda_available:
                    print(f"CUDA version: {torch.version.cuda}")
                    print(f"GPU device: {torch.cuda.get_device_name(0)}")
                
                # Use GPU if available
                self._device = torch.device('cuda' if cuda_available else 'cpu')
                
                # Initialize MTCNN for face detection
                
                self.mtcnn = MTCNN(
                    image_size=160,
                    margin=20,
                    min_face_size=20,
                    thresholds=[0.6, 0.7, 0.7],
                    factor=0.709,
                    post_process=True,
                    device=self._device,
                    keep_all=False  
                )
                
                
                self.resnet = InceptionResnetV1(
                    pretrained='vggface2',
                    classify=False,
                    device=self._device
                ).eval()
                
                
                self.resnet = self.resnet.to(self._device)
                
                self._initialized = True
                print(f"FaceNet initialized on device: {self._device}")
            except Exception as e:
                print(f"Failed to initialize FaceNet: {e}")
                import traceback
                traceback.print_exc()
                self._initialized = True  
        return self.mtcnn, self.resnet
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better face detection.
        - Resize if too small
        - Convert color space if needed
        """
        if image is None:
            return None
        
        
        if len(image.shape) == 2:
            
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        elif image.shape[2] == 3:
            
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        
        h, w = image.shape[:2]
        
        
        min_size = 160
        if h < min_size or w < min_size:
            scale = max(min_size / h, min_size / w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            print(f"Resized image from ({w}, {h}) to ({new_w}, {new_h})")
        
        return image
    
    def process(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Process face image and return 512-D FaceNet embedding.
        
        Args:
            image_bytes: Raw image bytes (JPEG)
            
        Returns:
            512-D float32 embedding or None if face not detected
        """
        try:
            import torch
            from PIL import Image
            
            
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                print("Failed to decode image")
                return None
            
            print(f"Original image size: {image.shape}")
            
            
            image = self.preprocess_image(image)
            
            if image is None:
                print("Image preprocessing failed")
                return None
            
            
            mtcnn, resnet = self._get_models()
            if mtcnn is None or resnet is None:
                print("FaceNet models not initialized")
                return None
            
            
            pil_image = Image.fromarray(image)
            
            
            face_tensor = mtcnn(pil_image)
            
            if face_tensor is None:
                print(f"No face detected in image (size: {image.shape})")
                return None
            
            
            if face_tensor.dim() == 3:
                face_tensor = face_tensor.unsqueeze(0)
            face_tensor = face_tensor.to(self._device)
            
            
            with torch.no_grad():
                embedding = resnet(face_tensor)
                embedding = embedding.squeeze().cpu().numpy()
            
            print(f"Face detected! Embedding shape: {embedding.shape}")
            
            
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
    Falls back to MFCC if SpeechBrain fails.
    """
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.encoder = None
        self._initialized = False
        self._use_fallback = False
    
    def _get_encoder(self):
        """Lazy initialization of SpeechBrain speaker encoder."""
        if not self._initialized:
            try:
                
                import torch
                import torchaudio
                
                
                try:
                    if hasattr(torchaudio, 'list_audio_backends'):
                        backends = torchaudio.list_audio_backends()
                        print(f"Available audio backends: {backends}")
                except Exception:
                    pass
                
                from speechbrain.inference import EncoderClassifier
                
                from speechbrain.utils.fetching import LocalStrategy
                
                
                
                self.encoder = EncoderClassifier.from_hparams(
                    source="speechbrain/spkrec-ecapa-voxceleb",
                    savedir="data/speechbrain_models/spkrec-ecapa-voxceleb",
                    run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"},
                    local_strategy=LocalStrategy.COPY
                )
                self._initialized = True
                print(f"SpeechBrain ECAPA-TDNN model loaded (device: {'cuda' if torch.cuda.is_available() else 'cpu'})")
            except ImportError as e:
                
                try:
                    import torch
                    from speechbrain.pretrained import EncoderClassifier
                    from speechbrain.utils.fetching import LocalStrategy
                    
                    self.encoder = EncoderClassifier.from_hparams(
                        source="speechbrain/spkrec-ecapa-voxceleb",
                        savedir="data/speechbrain_models/spkrec-ecapa-voxceleb",
                        run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"},
                        local_strategy=LocalStrategy.COPY
                    )
                    self._initialized = True
                    print("SpeechBrain loaded via pretrained import path")
                except Exception as e2:
                    print(f"Failed to initialize SpeechBrain: {e2}")
                    self._use_fallback = True
                    self._initialized = True
            except Exception as e:
                print(f"Failed to initialize SpeechBrain: {e}")
                import traceback
                traceback.print_exc()
                self._use_fallback = True
                self._initialized = True
        return self.encoder
    
    def process(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """
        Process voice audio and return 192-D speaker embedding.
        
        Includes enhanced preprocessing for better accuracy:
        - Audio normalization
        - Noise reduction
        - Voice activity detection (trimming silence)
        - Minimum 3-second requirement for better embeddings
        
        Args:
            audio_bytes: Raw audio bytes (WAV/WebM format)
            
        Returns:
            192-D float32 embedding or None on error
        """
        try:
            
            audio_io = io.BytesIO(audio_bytes)
            y, sr = librosa.load(audio_io, sr=self.sample_rate)
            
            if len(y) == 0:
                print("Empty audio")
                return None
            
            
            
            
            max_val = np.max(np.abs(y))
            if max_val > 0:
                y = y / max_val * 0.95  
            
            
            y = y - np.mean(y)
            
            
            
            y_trimmed, _ = librosa.effects.trim(y, top_db=25)
            
            
            if len(y_trimmed) > self.sample_rate * 0.5:  
                y = y_trimmed
                print(f"Audio trimmed: {len(y)/self.sample_rate:.2f}s of speech detected")
            
            
            pre_emphasis = 0.97
            y = np.append(y[0], y[1:] - pre_emphasis * y[:-1])
            
            
            min_duration = 3 * self.sample_rate
            if len(y) < min_duration:
                
                repeats = int(np.ceil(min_duration / len(y)))
                y = np.tile(y, repeats)[:min_duration]
                print(f"Audio repeated to reach {min_duration/self.sample_rate:.1f}s minimum")
            
            
            max_val = np.max(np.abs(y))
            if max_val > 0:
                y = y / max_val * 0.95
            
            
            encoder = self._get_encoder()
            
            if encoder is None or self._use_fallback:
                print("Using MFCC fallback for voice embedding")
                return self._fallback_mfcc(y, sr)
            
            import torch
            
            
            device = next(encoder.mods.parameters()).device
            
            
            audio_tensor = torch.tensor(y).unsqueeze(0).float().to(device)
            
            
            with torch.no_grad():
                embedding = encoder.encode_batch(audio_tensor)
                embedding = embedding.squeeze().cpu().numpy()
            
            print(f"Voice embedding extracted, shape: {embedding.shape}")
            
            
            embedding = embedding.astype(np.float32)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            print(f"Voice processing error: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                audio_io = io.BytesIO(audio_bytes)
                y, sr = librosa.load(audio_io, sr=self.sample_rate)
                return self._fallback_mfcc(y, sr)
            except:
                return None
    
    def _fallback_mfcc(self, y: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """Fallback MFCC embedding if SpeechBrain fails."""
        try:
            
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
            
            
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)
            mfcc_delta = np.mean(librosa.feature.delta(mfccs), axis=1)
            mfcc_delta2 = np.mean(librosa.feature.delta(mfccs, order=2), axis=1)
            
            
            embedding = np.concatenate([mfcc_mean, mfcc_std, mfcc_delta, mfcc_delta2])
            
            
            if len(embedding) < 192:
                embedding = np.pad(embedding, (0, 192 - len(embedding)))
            else:
                embedding = embedding[:192]
            
            
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
        
        
        import torch
        self.reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
        
        
        self.face_processor = FaceProcessor()
        
        
        self.text_dim = 128
    
    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from document using OCR."""
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return ""
        
        
        results = self.reader.readtext(image)
        
        
        text_parts = [result[1] for result in results]
        return " ".join(text_parts)
    
    def text_to_embedding(self, text: str) -> np.ndarray:
        """
        Convert text to a simple embedding using character-level features.
        """
        if not text:
            return np.zeros(self.text_dim, dtype=np.float32)
        
        
        text_lower = text.lower()
        char_freq = np.zeros(26 + 10, dtype=np.float32)  
        
        for char in text_lower:
            if 'a' <= char <= 'z':
                char_freq[ord(char) - ord('a')] += 1
            elif '0' <= char <= '9':
                char_freq[26 + int(char)] += 1
        
        
        if char_freq.sum() > 0:
            char_freq = char_freq / char_freq.sum()
        
        
        np.random.seed(43)
        projection = np.random.randn(36, self.text_dim).astype(np.float32)
        embedding = np.dot(char_freq, projection)
        
        
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding.astype(np.float32)
    
    def preprocess_document_image(self, image: np.ndarray) -> np.ndarray:
        """
        Enhanced preprocessing specifically for ID document photos.
        Improves face detection accuracy on passport/ID photos.
        """
        if image is None:
            return None
        
        # Convert to RGB if needed
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        elif image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize to reasonable dimensions for better face detection
        h, w = image.shape[:2]
        target_size = 800
        if max(h, w) > target_size:
            scale = target_size / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        elif min(h, w) < 200:
            scale = 200 / min(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Apply bilateral filter for noise reduction while preserving edges
        # This helps with low quality ID photos
        image = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # This helps with varied lighting in ID photos
        # Increased clip limit for better contrast on ID photos
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        
        # Lighter sharpening to avoid over-processing
        # Over-sharpening can distort facial features
        kernel = np.array([[-0.2, -0.2, -0.2],
                          [-0.2,  2.6, -0.2],
                          [-0.2, -0.2, -0.2]])
        image = cv2.filter2D(image, -1, kernel)
        image = np.clip(image, 0, 255).astype(np.uint8)
        
        return image
    
    def extract_face_from_document(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Enhanced face extraction from ID documents with multiple attempts.
        Uses progressively relaxed parameters to find faces in difficult images.
        """
        try:
            import torch
            from PIL import Image
            from facenet_pytorch import MTCNN, InceptionResnetV1
            
            # Decode image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                print("Failed to decode document image")
                return None
            
            # Apply document-specific preprocessing
            image = self.preprocess_document_image(image)
            if image is None:
                return None
            
            print(f"Document image preprocessed: {image.shape}")
            
            # Get models
            mtcnn, resnet = self.face_processor._get_models()
            if mtcnn is None or resnet is None:
                return None
            
            device = self.face_processor._device
            pil_image = Image.fromarray(image)
            
            # First attempt with standard detection
            face_tensor = mtcnn(pil_image)
            
            # If no face found, try with more lenient settings
            if face_tensor is None:
                print("Standard detection failed, trying lenient thresholds...")
                
                # Create temporary MTCNN with relaxed thresholds
                lenient_mtcnn = MTCNN(
                    image_size=160,
                    margin=40,  # Larger margin
                    min_face_size=15,  # Smaller minimum face
                    thresholds=[0.5, 0.6, 0.6],  # Lower thresholds
                    factor=0.709,
                    post_process=True,
                    device=device,
                    keep_all=False
                )
                face_tensor = lenient_mtcnn(pil_image)
            
            # If still no face, try even more relaxed settings
            if face_tensor is None:
                print("Lenient detection failed, trying very relaxed thresholds...")
                
                very_lenient_mtcnn = MTCNN(
                    image_size=160,
                    margin=60,  # Even larger margin
                    min_face_size=10,  # Very small minimum
                    thresholds=[0.4, 0.5, 0.5],  # Very low thresholds
                    factor=0.709,
                    post_process=True,
                    device=device,
                    keep_all=False
                )
                face_tensor = very_lenient_mtcnn(pil_image)
            
            if face_tensor is None:
                print("No face detected in document after multiple attempts")
                return None
            
            # Extract embedding
            if face_tensor.dim() == 3:
                face_tensor = face_tensor.unsqueeze(0)
            face_tensor = face_tensor.to(device)
            
            with torch.no_grad():
                embedding = resnet(face_tensor)
                embedding = embedding.squeeze().cpu().numpy()
            
            print(f"Document face detected! Embedding shape: {embedding.shape}")
            
            # Normalize
            embedding = embedding.astype(np.float32)
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            print(f"Document face extraction error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process(self, image_bytes: bytes) -> Tuple[Optional[np.ndarray], str]:
        """
        Process document and return embedding and extracted text.
        
        The combined embedding format:
        - First 512 dims: Normalized face embedding (preserved for direct comparison)
        - Next 128 dims: Normalized text embedding
        
        IMPORTANT: Face portion is stored pre-normalized so it can be directly
        compared with live face embeddings without being affected by text portion.
        
        Args:
            image_bytes: Raw image bytes (JPEG)
            
        Returns:
            Tuple of (embedding, extracted text)
        """
        
        text = self.extract_text(image_bytes)
        print(f"Extracted text from document: {text[:100]}..." if len(text) > 100 else f"Extracted text: {text}")
        
        # Use enhanced document face extraction
        face_embedding = self.extract_face_from_document(image_bytes)
        
        # Text embedding (already normalized in text_to_embedding)
        text_embedding = self.text_to_embedding(text)
        
        if face_embedding is not None:
            # IMPORTANT: Keep face embedding normalized separately
            # This preserves the face vector's magnitude for accurate cosine similarity
            # when comparing with live face during verification
            face_normalized = face_embedding / (np.linalg.norm(face_embedding) + 1e-8)
            
            # Combine embeddings - face portion stays pre-normalized
            combined = np.concatenate([face_normalized.astype(np.float32), text_embedding])
            print(f"Document face embedding extracted successfully")
        else:
            # No face detected - use zeros
            combined = np.concatenate([
                np.zeros(512, dtype=np.float32),
                text_embedding
            ])
            print(f"Warning: No face detected in document")
        
        # DON'T normalize the combined vector as a whole!
        # This would scale down the face portion and reduce accuracy.
        # Each component is already normalized individually.
        
        return combined.astype(np.float32), text


class MLEngine:
    """Main ML engine combining all biometric processors."""
    
    def __init__(self):
        self.face_processor = FaceProcessor()
        self.voice_processor = VoiceProcessor()
        self.document_processor = DocumentProcessor()
    
    def process_face(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Process face image and return 512-D FaceNet embedding."""
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
