import logging
import json
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from generator import generate_enriched_description, extract_keywords

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "service":"description_service", "level":"%(levelname)s", "message":"%(message)s"}',
)
logger = logging.getLogger("describer")

app = FastAPI(
    title="Catalog Description & Recommendation Microservice",
    description="Stateless copy generation and keyword extraction service deployed on GCP Cloud Run.",
    version="1.0.0",
)


class GenerateRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID passed purely for isolated audit logging")
    raw_title: str
    raw_description: Optional[str] = None
    category_path: Optional[str] = None


class GenerateResponse(BaseModel):
    generated_description: str
    keywords: List[str]


@app.post("/generate", response_model=GenerateResponse)
def generate_endpoint(req: GenerateRequest):
    """
    Stateless description generation endpoint.
    Isolation Guarantee (§6.4):
    - Request context is strictly ephemeral.
    - No caching without tenant context.
    - Tenant ID is recorded in structured logs for observability.
    """
    try:
        enriched_copy = generate_enriched_description(
            title=req.raw_title,
            raw_desc=req.raw_description,
            category_path=req.category_path,
        )
        tags = extract_keywords(f"{req.raw_title} {req.raw_description or ''}")

        log_payload = {
            "tenant_id": req.tenant_id,
            "title_length": len(req.raw_title),
            "generated_length": len(enriched_copy),
            "keyword_count": len(tags),
        }
        logger.info(f"Generated description: {json.dumps(log_payload)}")

        return GenerateResponse(generated_description=enriched_copy, keywords=tags)
    except Exception as e:
        logger.error(f"Generation error for tenant {req.tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Generation failure")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "description_service"}
