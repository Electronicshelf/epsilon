"""
OCR model wrapper - extracts text from images.

Uses a backend abstraction to support multiple OCR providers.
"""

from typing import List, Dict, Any
from abc import ABC, abstractmethod
import sys
import os
from io import BytesIO
import uuid
from datetime import datetime

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from schemas.models import Signal, SignalType

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCRBackend(ABC):
    """
    Abstract base class for OCR backends.
    
    All OCR backends must implement extract_text_data which returns
    a list of dictionaries with OCR detection results.
    """
    
    @abstractmethod
    def extract_text_data(self, image_data: bytes) -> List[Dict[str, Any]]:
        """
        Extract text data from image.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of dictionaries with OCR results. Each dict should have:
            - type: str (e.g., "ocr_text")
            - value: str (detected text)
            - confidence: float (0.0 to 1.0)
            - source: str (e.g., "image")
            - bbox: List[int] (x, y, width, height)
        """
        pass


class TesseractOCRBackend(OCRBackend):
    """
    Tesseract OCR backend using pytesseract.
    
    Uses pytesseract.image_to_data to get detailed OCR results
    including bounding boxes and confidence scores.
    """
    
    def __init__(self):
        if not TESSERACT_AVAILABLE:
            raise ImportError(
                "pytesseract and Pillow are required for TesseractOCRBackend. "
                "Install with: pip install pytesseract pillow"
            )
        self.backend_name = "tesseract"
    
    def extract_text_data(self, image_data: bytes) -> List[Dict[str, Any]]:
        """
        Extract text data using Tesseract OCR.
        
        Uses image_to_data to get detailed results including:
        - Individual word/token detections
        - Bounding boxes
        - Confidence scores
        
        Filters out:
        - Empty text
        - Confidence < 40 (Tesseract uses 0-100 scale)
        """
        # Load image from bytes
        image = Image.open(BytesIO(image_data))
        
        # Get detailed OCR data (not just string)
        # image_to_data returns a pandas DataFrame or dict-like structure
        # We'll use output_dict format for easier parsing
        ocr_data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT
        )
        
        results = []
        
        # Process each detected text element
        # ocr_data is a dict with lists: {'text': [...], 'conf': [...], 'left': [...], etc.}
        num_detections = len(ocr_data.get('text', []))
        
        for i in range(num_detections):
            text = ocr_data.get('text', [])[i]
            conf = ocr_data.get('conf', [])[i]
            left = ocr_data.get('left', [])[i]
            top = ocr_data.get('top', [])[i]
            width = ocr_data.get('width', [])[i]
            height = ocr_data.get('height', [])[i]
            
            # Filter out empty text
            if not text or not text.strip():
                continue
            
            # Filter out low confidence (Tesseract uses 0-100, we want >= 40)
            # Also filter out -1 (invalid confidence)
            if conf == -1 or conf < 40:
                continue
            
            # Normalize confidence from 0-100 to 0-1
            normalized_confidence = conf / 100.0
            
            # Create result dictionary
            result = {
                "type": "ocr_text",
                "value": text.strip(),
                "confidence": normalized_confidence,
                "source": "image",
                "bbox": [int(left), int(top), int(width), int(height)]
            }
            
            results.append(result)
        
        return results


def get_ocr_backend(backend_type: str = "tesseract") -> OCRBackend:
    """
    Factory function to get OCR backend instance.
    
    Args:
        backend_type: Type of backend ("tesseract", "google_vision", etc.)
        
    Returns:
        OCRBackend instance
        
    Raises:
        ValueError: If backend_type is not supported
        ImportError: If required dependencies are missing
    """
    if backend_type == "tesseract":
        return TesseractOCRBackend()
    elif backend_type == "google_vision":
        # Placeholder for future Google Vision API backend
        raise ValueError("Google Vision backend not yet implemented")
    else:
        raise ValueError(f"Unsupported OCR backend type: {backend_type}")


class OCRModel:
    """
    OCR model wrapper that uses backend abstraction.
    
    Converts backend dictionary results to Signal objects.
    """
    
    def __init__(self, backend: OCRBackend = None):
        """
        Initialize OCR model.
        
        Args:
            backend: OCRBackend instance. If None, uses default (Tesseract).
        """
        if backend is None:
            try:
                self.backend = get_ocr_backend("tesseract")
                self.model_name = "ocr_tesseract"
            except (ImportError, ValueError) as e:
                # Fallback to placeholder if Tesseract not available
                self.backend = None
                self.model_name = "ocr_placeholder"
        else:
            self.backend = backend
            self.model_name = f"ocr_{backend.backend_name}"
    
    def extract_text(self, image_data: bytes) -> List[Signal]:
        """
        Extract text from image and return as Signal objects.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of Signal objects containing detected text
        """
        # If no backend available, return empty list
        if self.backend is None:
            return []
        
        # Get OCR data from backend
        ocr_results = self.backend.extract_text_data(image_data)
        
        # Convert dictionaries to Signal objects
        signals = []
        for ocr_result in ocr_results:
            # Extract bounding box
            bbox_list = ocr_result.get("bbox", [0, 0, 0, 0])
            if len(bbox_list) == 4:
                bbox = {
                    "x": float(bbox_list[0]),
                    "y": float(bbox_list[1]),
                    "width": float(bbox_list[2]),
                    "height": float(bbox_list[3])
                }
            else:
                bbox = None
            
            # Create Signal object
            signal = Signal(
                signal_id=str(uuid.uuid4()),
                signal_type=SignalType.TEXT,
                source_model=self.model_name,
                confidence=ocr_result.get("confidence", 0.0),
                raw_data={
                    "text": ocr_result.get("value", ""),
                    "type": ocr_result.get("type", "ocr_text"),
                    "source": ocr_result.get("source", "image"),
                    "bbox": bbox_list
                },
                bounding_box=bbox,
                detected_at=datetime.now()
            )
            
            signals.append(signal)
        
        return signals
    
    def _parse_ocr_result(self, ocr_output: Dict[str, Any]) -> List[Signal]:
        """
        Parse OCR model output into Signal objects.
        
        This method is kept for backward compatibility but is not used
        when using the backend abstraction.
        """
        signals = []
        # This method is deprecated in favor of backend abstraction
        return signals
