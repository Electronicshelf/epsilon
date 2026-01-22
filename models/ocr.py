"""
OCR model wrapper - extracts text from images.
"""

from typing import List, Dict, Any
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from schemas.models import Signal, SignalType


class OCRModel:
    """Placeholder OCR model that extracts text from images."""
    
    def __init__(self):
        self.model_name = "ocr_placeholder"
    
    def extract_text(self, image_data: bytes) -> List[Signal]:
        """
        Extract text from image.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            List of Signal objects containing detected text
        """
        # Placeholder: In production, this would call actual OCR (e.g., Tesseract, Google Vision API)
        # For now, return empty list or simulate detection
        return []
    
    def _parse_ocr_result(self, ocr_output: Dict[str, Any]) -> List[Signal]:
        """Parse OCR model output into Signal objects."""
        signals = []
        # Placeholder implementation
        return signals
