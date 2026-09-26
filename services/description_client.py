import logging
from typing import Optional, List, Dict, Any
import httpx
from config import settings

logger = logging.getLogger(__name__)


def _stub_generate_description(item_title: str, item_desc: Optional[str], category_path: Optional[str]) -> str:
    """High quality fallback / stub description generator for offline dev/testing."""
    desc_part = f" Details: {item_desc}" if item_desc else ""
    cat_part = f" Optimized for {category_path}." if category_path else ""
    return (
        f"Discover the premium performance of '{item_title}'.{desc_part}"
        f"{cat_part} Engineered to elevate standards with exceptional quality and enduring durability."
    )


def generate_description(
    tenant_id: str,
    raw_title: str,
    raw_description: Optional[str] = None,
    category_path: Optional[str] = None,
) -> str:
    """
    Client for Description/Recommendation Generation Service (Cloud Run / Microservice).
    Stateless per-request execution.
    """
    if settings.USE_ML_STUBS:
        return _stub_generate_description(raw_title, raw_description, category_path)

    payload = {
        "tenant_id": str(tenant_id),
        "raw_title": raw_title,
        "raw_description": raw_description or "",
        "category_path": category_path or "",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{settings.DESCRIPTION_SERVICE_URL}/generate", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["generated_description"]
            else:
                logger.warning(
                    f"Description service returned HTTP {resp.status_code}. Using fallback.",
                    extra={"tenant_id": tenant_id},
                )
                return _stub_generate_description(raw_title, raw_description, category_path)
    except Exception as e:
        logger.warning(
            f"Failed to reach description service ({e}). Using deterministic fallback.",
            extra={"tenant_id": tenant_id},
        )
        return _stub_generate_description(raw_title, raw_description, category_path)
