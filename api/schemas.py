from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class CatalogItemCreate(BaseModel):
    sku: str = Field(..., max_length=255, description="Unique product SKU for the tenant")
    raw_title: str = Field(..., description="Raw title of the catalog item")
    raw_description: Optional[str] = Field(None, description="Raw product description or specifications")


class CatalogItemBatchIngest(BaseModel):
    items: List[CatalogItemCreate] = Field(..., min_length=1, max_length=1000)


class CatalogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    sku: str
    raw_title: Optional[str]
    raw_description: Optional[str]
    generated_description: Optional[str]
    category_path: Optional[str]
    classification_confidence: Optional[Decimal]
    status: str
    created_at: datetime
    updated_at: datetime


class CatalogItemListResponse(BaseModel):
    items: List[CatalogItemResponse]
    total: int
    limit: int
    offset: int


class CatalogRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    source_item_id: UUID
    recommended_item_id: UUID
    score: Decimal
    created_at: datetime


class AccessAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: UUID
    actor: str
    action: str
    resource: str
    occurred_at: datetime


class AuditLogListResponse(BaseModel):
    logs: List[AccessAuditLogResponse]
    total: int
    limit: int
    offset: int


class ReprocessResponse(BaseModel):
    message: str
    enqueued_count: int


class IngestResponse(BaseModel):
    message: str
    ingested_count: int
    item_ids: List[UUID]


class TokenRequest(BaseModel):
    tenant_id: Optional[str] = None
    actor: str
    role: str = "tenant_user"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class HealthCheckResponse(BaseModel):
    status: str
    environment: str
    database: str
    redis: str
