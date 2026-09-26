import hashlib
import logging
from dataclasses import dataclass
from typing import Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    path: str
    confidence: float


# Heuristic rule-based taxonomy fallback for offline testing or when service is down
TAXONOMY_MAP = {
    "electronics": ["phone", "laptop", "headphone", "audio", "camera", "tv", "charger", "cable", "wireless", "gadget"],
    "apparel": ["shirt", "pants", "dress", "shoes", "jacket", "hoodie", "cotton", "denim", "sneakers"],
    "home_kitchen": ["blender", "cookware", "pan", "knife", "towel", "pillow", "furniture", "lamp", "desk"],
    "sports_outdoors": ["ball", "gym", "yoga", "running", "bicycle", "tent", "fitness", "dumbbell"],
    "books_media": ["novel", "book", "guide", "paperback", "hardcover", "journal"],
}


def _stub_classify(text: str) -> ClassificationResult:
    """Deterministic fallback/stub classifier for development and testing."""
    text_lower = (text or "").lower()
    for category, keywords in TAXONOMY_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return ClassificationResult(
                    path=f"{category.replace('_', ' ').title()} > General",
                    confidence=0.92,
                )
    return ClassificationResult(
        path="General Merchandise > Uncategorized",
        confidence=0.75,
    )


def classify(tenant_id: str, text: str) -> ClassificationResult:
    """
    Client for the Classification Service (Cloud Run / Microservice).
    Passes tenant_id purely for isolated structured logging / auditing.
    """
    if settings.USE_ML_STUBS:
        return _stub_classify(text)

    payload = {
        "tenant_id": str(tenant_id),
        "text": text or "",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{settings.CLASSIFICATION_SERVICE_URL}/classify", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return ClassificationResult(
                    path=data["category_path"],
                    confidence=float(data["confidence"]),
                )
            else:
                logger.warning(
                    f"Classification service returned HTTP {resp.status_code}. Using fallback.",
                    extra={"tenant_id": tenant_id},
                )
                return _stub_classify(text)
    except Exception as e:
        logger.warning(
            f"Failed to reach classification service ({e}). Using deterministic fallback.",
            extra={"tenant_id": tenant_id},
        )
        return _stub_classify(text)
