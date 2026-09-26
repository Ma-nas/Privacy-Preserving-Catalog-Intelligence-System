#!/usr/bin/env python3
"""
Seed script for generating test tenants, initial catalog items, and JWT tokens.
"""

import sys
import uuid
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from db.engine import engine
from db.models import Tenant, CatalogItem
from db.session import tenant_scoped_session, write_audit_log
from api.auth import create_access_token


def seed_database():
    print("[*] Connecting to database...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"[!] Unable to connect to database: {e}")
        print("    Ensure PostgreSQL is running and migrations are applied.")
        return

    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()

    print(f"[*] Creating Tenant A: Apex Electronics ({tenant_a_id})")
    print(f"[*] Creating Tenant B: Zenith Fashion & Goods ({tenant_b_id})")

    with Session(engine) as session:
        tenant_a = Tenant(id=tenant_a_id, name="Apex Electronics Inc.")
        tenant_b = Tenant(id=tenant_b_id, name="Zenith Fashion & Goods")
        session.add_all([tenant_a, tenant_b])
        session.commit()

    # Seed Tenant A Items
    with tenant_scoped_session(str(tenant_a_id)) as db:
        items_a = [
            CatalogItem(
                tenant_id=tenant_a_id,
                sku="APEX-AUD-01",
                raw_title="Apex Ultra Wireless ANC Headphones",
                raw_description="Over-ear active noise cancelling with 40-hour battery life.",
                status="pending",
            ),
            CatalogItem(
                tenant_id=tenant_a_id,
                sku="APEX-MOU-02",
                raw_title="Apex Ergonomic Precision Wireless Mouse",
                raw_description="High DPI sensor with thumb rest and multi-device pairing.",
                status="pending",
            ),
        ]
        db.add_all(items_a)
        write_audit_log(db, str(tenant_a_id), "seed_script", "write", "catalog_items:seed_tenant_a")

    # Seed Tenant B Items
    with tenant_scoped_session(str(tenant_b_id)) as db:
        items_b = [
            CatalogItem(
                tenant_id=tenant_b_id,
                sku="ZEN-SHIRT-01",
                raw_title="Zenith Organic Cotton Slim-Fit Crewneck",
                raw_description="100% sustainable combed organic cotton tee.",
                status="pending",
            ),
            CatalogItem(
                tenant_id=tenant_b_id,
                sku="ZEN-JACKET-02",
                raw_title="Zenith All-Weather Urban Windbreaker",
                raw_description="Breathable water-resistant outer shell with reflective accents.",
                status="pending",
            ),
        ]
        db.add_all(items_b)
        write_audit_log(db, str(tenant_b_id), "seed_script", "write", "catalog_items:seed_tenant_b")

    print("\n[SUCCESS] Seed completed successfully!")
    print("\n--- Test Authentication Credentials ---")
    token_a = create_access_token(tenant_id=str(tenant_a_id), actor="tenant_a_admin", role="tenant_admin")
    token_b = create_access_token(tenant_id=str(tenant_b_id), actor="tenant_b_admin", role="tenant_admin")
    token_auditor = create_access_token(tenant_id=None, actor="compliance_officer", role="auditor")

    print(f"Tenant A Token: Bearer {token_a}\n")
    print(f"Tenant B Token: Bearer {token_b}\n")
    print(f"Auditor Token:  Bearer {token_auditor}\n")


if __name__ == "__main__":
    seed_database()
