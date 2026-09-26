import logging
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from model import CatalogClassifier

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "service":"classification_service", "level":"%(levelname)s", "message":"%(message)s"}',
)
logger = logging.getLogger("classifier")

app = FastAPI(
    title="Catalog Classification Microservice",
    description="Stateless scikit-learn classifier service deployed on GCP Cloud Run.",
    version="1.0.0",
)


class ClassifyRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID passed purely for isolated audit logging")
    text: str = Field(..., description="Raw product title or description")


class ClassifyResponse(BaseModel):
    category_path: str
    confidence: float


@app.post("/classify", response_model=ClassifyResponse)
def classify_endpoint(req: ClassifyRequest):
    """
    Stateless classification endpoint.
    Isolation Guarantee (§6.4):
    - Request context is strictly ephemeral.
    - No caching without tenant context.
    - Tenant ID is recorded in structured logs for observability.
    """
    try:
        category, confidence = CatalogClassifier.predict(req.text)
        
        # Structured log without cross-tenant mixing
        log_payload = {
            "tenant_id": req.tenant_id,
            "text_length": len(req.text),
            "predicted_category": category,
            "confidence": confidence,
        }
        logger.info(f"Classified item: {json.dumps(log_payload)}")

        return ClassifyResponse(category_path=category, confidence=confidence)
    except Exception as e:
        logger.error(f"Inference error for tenant {req.tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Inference failure")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "classification_service"}
