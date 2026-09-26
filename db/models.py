import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    catalog_items = relationship("CatalogItem", back_populates="tenant", cascade="all, delete-orphan")


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku = Column(String(255), nullable=False)
    raw_title = Column(Text, nullable=True)
    raw_description = Column(Text, nullable=True)
    generated_description = Column(Text, nullable=True)
    category_path = Column(Text, nullable=True)
    classification_confidence = Column(Numeric(4, 3), nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending | enriched | failed
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_tenant_sku"),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="catalog_items")
    recommendations_as_source = relationship(
        "CatalogRecommendation",
        foreign_keys="CatalogRecommendation.source_item_id",
        back_populates="source_item",
        cascade="all, delete-orphan",
    )
    recommendations_as_target = relationship(
        "CatalogRecommendation",
        foreign_keys="CatalogRecommendation.recommended_item_id",
        back_populates="recommended_item",
    )


class CatalogRecommendation(Base):
    __tablename__ = "catalog_recommendations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommended_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score = Column(Numeric(5, 4), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    source_item = relationship("CatalogItem", foreign_keys=[source_item_id], back_populates="recommendations_as_source")
    recommended_item = relationship("CatalogItem", foreign_keys=[recommended_item_id], back_populates="recommendations_as_target")


class AccessAuditLog(Base):
    __tablename__ = "access_audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor = Column(String(255), nullable=False)  # service account / user id
    action = Column(String(50), nullable=False)  # 'read' | 'write' | 'enrich' | 'export'
    resource = Column(Text, nullable=False)       # table/row reference, e.g. catalog_items:<item_id>
    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
