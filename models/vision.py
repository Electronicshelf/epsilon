"""
Vision model wrapper - detects objects, faces, scenes, etc.
"""

from typing import List, Dict, Any, Optional
import sys
import os
import uuid
from io import BytesIO

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from schemas.models import Signal, SignalType
from datetime import datetime

try:
    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
    GROUNDING_DINO_AVAILABLE = True
except ImportError:
    GROUNDING_DINO_AVAILABLE = False


VISION_OBJECT_QUERIES = [
    "weapon",
    "gun",
    "knife",
    "pill",
    "medicine",
    "syringe",
    "money",
    "cash",
    "banknote",
]

# Module-level model cache (lazy singleton)
_dino_model: Optional["AutoModelForZeroShotObjectDetection"] = None
_dino_processor: Optional["AutoProcessor"] = None


class VisionModel:
    """Grounding DINO vision model (object detection only, v1)."""
    
    def __init__(self):
        self.model_name = "grounding_dino"
        self._model = None
        self._processor = None
        self._device = "cpu"

    def _load_model(self) -> None:
        """Lazy load Grounding DINO once (CPU-only)."""
        if not GROUNDING_DINO_AVAILABLE:
            raise ImportError(
                "Grounding DINO requires transformers, torch, and pillow. "
                "Install deps and ensure the model is available locally."
            )

        global _dino_model, _dino_processor
        if _dino_model is None or _dino_processor is None:
            model_id = "IDEA-Research/grounding-dino-base"
            _dino_processor = AutoProcessor.from_pretrained(model_id)
            _dino_model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id)
            _dino_model.eval()

        self._model = _dino_model
        self._processor = _dino_processor
    
    def detect_objects(self, image_data: bytes) -> List[Dict[str, Any]]:
        """
        Detect objects in image.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of dict payloads describing detected objects.
        """
        if not GROUNDING_DINO_AVAILABLE:
            return []

        self._load_model()

        # Load image from bytes
        image = Image.open(BytesIO(image_data))
        if image.mode != "RGB":
            image = image.convert("RGB")

        # One inference per image with fixed open-vocabulary prompts.
        # HF Grounding DINO expects classes separated (periods internally) and/or
        # provided as nested lists of labels.
        text_labels = [[q.lower() for q in VISION_OBJECT_QUERIES]]

        inputs = self._processor(images=image, text=text_labels, return_tensors="pt").to(self._device)
        with torch.no_grad():
            outputs = self._model(**inputs)

        # Post-process model outputs into boxes/scores/labels
        # target_sizes: (height, width)
        results = self._processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            threshold=0.3,
            text_threshold=0.3,
            target_sizes=[image.size[::-1]],
        )

        if not results:
            return []

        boxes = results[0].get("boxes", [])
        scores = results[0].get("scores", [])
        # Newer versions may return `text_labels` rather than `labels`
        labels = results[0].get("text_labels", results[0].get("labels", []))

        detections: List[Dict[str, Any]] = []
        for box, score, label in zip(boxes, scores, labels):
            conf = float(score)
            if conf < 0.3:
                continue

            # boxes are (x0, y0, x1, y1) in pixel coords
            x0, y0, x1, y1 = [float(v) for v in box.tolist()]
            w = max(0.0, x1 - x0)
            h = max(0.0, y1 - y0)

            payload = {
                "type": "vision_object",
                "label": str(label).strip().lower(),
                "confidence": conf,
                "bbox": [x0, y0, w, h],
                "source": "image",
                "model": "grounding_dino",
            }
            detections.append(payload)

        return detections
    
    def detect_faces(self, image_data: bytes) -> List[Signal]:
        """Detect faces in image."""
        return []
    
    def detect_brands(self, image_data: bytes) -> List[Signal]:
        """Detect brand logos in image."""
        return []
    
    def classify_scene(self, image_data: bytes) -> List[Signal]:
        """Classify scene/context of image."""
        return []
