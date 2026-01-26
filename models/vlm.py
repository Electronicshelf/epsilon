"""
VLM (Vision Language Model) wrapper - understands image content in context.
"""

from typing import List, Dict, Any
import sys
import os
import base64
import json
from io import BytesIO

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from schemas.models import Signal, SignalType

try:
    import requests
except ImportError:
    requests = None


def analyze_image_context(
    image_bytes: bytes,
    ocr_texts: List[str],
    vision_objects: List[Dict[str, Any]],
    policy_id: str,
) -> str:
    """
    Returns a short natural-language explanation (<= 3 sentences).

    Uses an API-based VLM (GPT-4o Vision) and MUST NOT return scores or verdicts.
    Reads API key from environment variable: VLM_API_KEY.
    """
    api_key = os.environ.get("VLM_API_KEY")
    if not api_key:
        raise RuntimeError("VLM_API_KEY is not set")
    if requests is None:
        raise ImportError("requests is required for VLM API calls")

    # Keep inputs concise (cost control)
    ocr_texts_clean = [t.strip() for t in (ocr_texts or []) if t and t.strip()]
    ocr_texts_clean = ocr_texts_clean[:25]

    objs = []
    for obj in vision_objects or []:
        label = str(obj.get("label", "")).strip()
        if not label:
            continue
        conf = obj.get("confidence", None)
        objs.append({"label": label, "confidence": conf})
    objs = objs[:25]

    policy_name = policy_id.replace("_", " ").strip()

    prompt = (
        "You are helping explain compliance evidence for an ad image.\n"
        "Be factual and neutral. Do NOT give a verdict, policy decision, or score.\n"
        "Respond with at most 3 sentences.\n\n"
        f"Policy: {policy_name}\n"
        f"OCR text snippets: {ocr_texts_clean}\n"
        f"Vision objects: {objs}\n\n"
        "Task: Briefly explain whether the image content and text supports the policy concern, "
        "and note any ambiguity (e.g., medical vs non-medical usage) if relevant."
    )

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/png;base64,{b64}"

    # OpenAI Chat Completions (vision)
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": 120,
        "temperature": 0.2,
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    resp.raise_for_status()
    out = resp.json()

    # Chat Completions response shape
    text = (
        (out.get("choices") or [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not isinstance(text, str):
        text = str(text)
    return text.strip()[:600]


class VLMModel:
    """Placeholder VLM model for contextual understanding."""
    
    def __init__(self):
        self.model_name = "gpt_4o_vision_api"
    
    def analyze_content(self, image_data: bytes, prompt: str = None) -> List[Signal]:
        """
        Analyze image content with language understanding.
        
        Args:
            image_data: Raw image bytes
            prompt: Optional prompt for specific analysis
            
        Returns:
            List of Signal objects with contextual understanding
        """
        # Placeholder: In production, this would call actual VLM
        # (e.g., GPT-4V, Claude Vision, LLaVA)
        return []
    
    def check_compliance_context(self, image_data: bytes, signals: List[Signal]) -> List[Signal]:
        """
        Use VLM to check compliance context given detected signals.
        
        Args:
            image_data: Raw image bytes
            signals: Previously detected signals
            
        Returns:
            Additional signals with compliance-relevant context
        """
        return []

    def analyze_image_context(
        self,
        image_bytes: bytes,
        ocr_texts: List[str],
        vision_objects: List[Dict[str, Any]],
        policy_id: str,
    ) -> str:
        return analyze_image_context(image_bytes, ocr_texts, vision_objects, policy_id)
