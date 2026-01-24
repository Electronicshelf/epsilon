"""
SigLIP embedding similarity model.
"""

from typing import List, Optional, Tuple
import sys
import os
import uuid
from io import BytesIO
from datetime import datetime
import numpy as np

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from schemas.models import Signal, SignalType

try:
    from transformers import AutoProcessor, AutoModel
    import torch
    from PIL import Image
    SIGLIP_AVAILABLE = True
except ImportError:
    SIGLIP_AVAILABLE = False


# Module-level model cache (lazy singleton)
_model: Optional[AutoModel] = None
_processor: Optional[AutoProcessor] = None
_device: Optional[str] = None

# In-memory cache for regulation text embeddings
_text_embedding_cache: dict[str, np.ndarray] = {}

# Regulations to compare image against: (name, text). Used for similarity signals.
REGULATION_TEXTS: List[Tuple[str, str]] = [
    ("misleading_claims", "misleading or exaggerated advertising claims"),
]
SIMILARITY_THRESHOLD = 0.6
EMBEDDING_MODEL_NAME = "siglip"


def _get_model():
    """Lazy singleton to load SigLIP model once."""
    global _model, _processor, _device
    
    if _model is None:
        if not SIGLIP_AVAILABLE:
            raise ImportError(
                "transformers and torch are required for SigLIP. "
                "Install with: pip install transformers torch pillow"
            )
        
        model_name = "google/siglip-base-patch16-224"
        _processor = AutoProcessor.from_pretrained(model_name)
        _model = AutoModel.from_pretrained(model_name)
        
        # Use GPU if available, otherwise CPU
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = _model.to(_device)
        _model.eval()
    
    return _model, _processor, _device


class EmbeddingSimilarityModel:
    """
    SigLIP-based embedding similarity model.
    Extracts normalized image embeddings for similarity comparison.
    """

    def __init__(self):
        self.model_name = "siglip"
        self._model = None
        self._processor = None
        self._device = None

    def _load_model(self):
        """Lazy load model on first use."""
        if self._model is None:
            self._model, self._processor, self._device = _get_model()

    def extract_embedding(self, image_data: bytes) -> np.ndarray:
        """
        Extract normalized image embedding vector.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Normalized embedding vector (unit length) as numpy array
        """
        self._load_model()
        
        # Load image from bytes
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Process image (processor returns pixel_values)
        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        
        # Image-only: use get_image_features to avoid requiring input_ids
        with torch.no_grad():
            features = self._model.get_image_features(**inputs)
            embedding = features[0].cpu().numpy()
        
        # Normalize to unit length
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.astype(np.float32)

    def extract_similarity(self, image_data: bytes) -> List[Signal]:
        """
        Compare image embedding to regulation text embeddings; emit a signal
        per regulation only when cosine similarity exceeds threshold.
        
        Embeddings are supporting evidence only; they do not trigger
        violations on their own. OCR text remains the primary trigger.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of signals with type "image_embedding_similarity" where
            similarity > threshold (0–1, conservative).
        """
        if not REGULATION_TEXTS:
            return []
        if not SIGLIP_AVAILABLE:
            return []
        self._load_model()
        image_emb = self.extract_embedding(image_data)
        texts = [t for _, t in REGULATION_TEXTS]
        text_embs = encode_regulation_texts(texts)
        names = [n for n, _ in REGULATION_TEXTS]
        signals: List[Signal] = []
        for name, text_emb in zip(names, text_embs):
            # Cosine similarity (both unit-length): dot product in [-1,1]
            cos_sim = float(np.dot(image_emb, text_emb))
            score = max(0.0, min(1.0, (cos_sim + 1.0) / 2.0))
            if score <= SIMILARITY_THRESHOLD:
                continue
            raw = {
                "type": "image_embedding_similarity",
                "regulation": name,
                "score": score,
                "model": EMBEDDING_MODEL_NAME,
            }
            sig = Signal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.SCENE,
                source_model=EMBEDDING_MODEL_NAME,
                confidence=score,
                raw_data=raw,
                bounding_box=None,
                detected_at=datetime.now(),
            )
            signals.append(sig)
        return signals


def encode_regulation_texts(texts: List[str]) -> List[np.ndarray]:
    """
    Encode regulation text strings into normalized embeddings using SigLIP.
    
    Uses the same SigLIP model's text encoder. Results are cached in memory
    to avoid recomputation for the same text strings.
    
    Args:
        texts: List of regulation text strings to encode
        
    Returns:
        List of normalized embedding vectors (unit length) as numpy arrays,
        one per input text. Order matches input list.
    """
    global _text_embedding_cache
    
    if not SIGLIP_AVAILABLE:
        raise ImportError(
            "transformers and torch are required for text encoding. "
            "Install with: pip install transformers torch"
        )
    
    # Load model if needed
    model, processor, device = _get_model()
    
    embeddings = []
    texts_to_encode = []
    text_indices = []
    
    # Check cache and collect texts that need encoding
    for i, text in enumerate(texts):
        if text in _text_embedding_cache:
            embeddings.append((i, _text_embedding_cache[text]))
        else:
            texts_to_encode.append(text)
            text_indices.append(i)
    
    # Encode texts not in cache
    if texts_to_encode:
        # Process text (processor returns input_ids, attention_mask)
        inputs = processor(text=texts_to_encode, return_tensors="pt", padding="max_length", truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Text-only: use get_text_features to avoid requiring pixel_values
        with torch.no_grad():
            text_embeds = model.get_text_features(**inputs).cpu().numpy()
        
        # Normalize and cache each embedding
        for idx, (text, embedding) in enumerate(zip(texts_to_encode, text_embeds)):
            # Normalize to unit length
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            embedding = embedding.astype(np.float32)
            
            # Cache the result
            _text_embedding_cache[text] = embedding
            
            # Store for output with original index
            embeddings.append((text_indices[idx], embedding))
    
    # Sort by original index and return embeddings only
    embeddings.sort(key=lambda x: x[0])
    return [emb for _, emb in embeddings]
