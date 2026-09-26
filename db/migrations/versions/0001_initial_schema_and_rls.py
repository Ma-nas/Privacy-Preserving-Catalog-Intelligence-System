"""Initial schema and RLS policies

Revision ID: 0001_initial_schema_and_rls
Revises: 
Create Date: 2026-09-26 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema_and_rls"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgcrypto extension for UUID generation
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # 2. Ensure application roles exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_role') THEN
                CREATE ROLE app_role;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auditor_role') THEN
                CREATE ROLE auditor_role;
            END IF;
        END
        $$;
    """)

    # 3. Create tenants table (not RLS protected - source of truth)
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Create catalog_items table
    op.create_table(
        "catalog_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=False),
        sa.Column("raw_title", sa.Text(), nullable=True),
        sa.Column("raw_description", sa.Text(), nullable=True),
        sa.Column("generated_description", sa.Text(), nullable=True),
        sa.Column("category_path", sa.Text(), nullable=True),
        sa.Column("classification_confidence", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_tenant_sku"),
    )
    op.create_index(op.f("ix_catalog_items_tenant_id"), "catalog_items", ["tenant_id"], unique=False)

    # 5. Create catalog_recommendations table
    op.create_table(
        "catalog_recommendations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommended_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_item_id"], ["catalog_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommended_item_id"], ["catalog_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catalog_recommendations_tenant_id"), "catalog_recommendations", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_catalog_recommendations_source_item_id"), "catalog_recommendations", ["source_item_id"], unique=False)
    op.create_index(op.f("ix_catalog_recommendations_recommended_item_id"), "catalog_recommendations", ["recommended_item_id"], unique=False)

    # 6. Create access_audit_log table
    op.create_table(
        "access_audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_audit_log_tenant_id"), "access_audit_log", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_access_audit_log_occurred_at"), "access_audit_log", ["occurred_at"], unique=False)

    # 7. Grant permissions to app_role and auditor_role
    op.execute("""
        GRANT USAGE ON SCHEMA public TO app_role, auditor_role;
        GRANT SELECT, INSERT, UPDATE, DELETE ON tenants, catalog_items, catalog_recommendations, access_audit_log TO app_role;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_role;
        GRANT SELECT ON access_audit_log TO auditor_role;
    """)

    # 8. Enable and FORCE Row-Level Security on all tenant data tables
    op.execute("""
        ALTER TABLE catalog_items ENABLE ROW LEVEL SECURITY;
        ALTER TABLE catalog_items FORCE ROW LEVEL SECURITY;

        ALTER TABLE catalog_recommendations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE catalog_recommendations FORCE ROW LEVEL SECURITY;

        ALTER TABLE access_audit_log ENABLE ROW LEVEL SECURITY;
        ALTER TABLE access_audit_log FORCE ROW LEVEL SECURITY;
    """)

    # 9. Create RLS Policies
    # catalog_items policies
    op.execute("""
        CREATE POLICY tenant_isolation_select ON catalog_items
        FOR SELECT
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

        CREATE POLICY tenant_isolation_write ON catalog_items
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
    """)

    # catalog_recommendations policies
    op.execute("""
        CREATE POLICY tenant_isolation_select ON catalog_recommendations
        FOR SELECT
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

        CREATE POLICY tenant_isolation_write ON catalog_recommendations
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
    """)

    # access_audit_log policies
    op.execute("""
        CREATE POLICY tenant_isolation_select ON access_audit_log
        FOR SELECT
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

        CREATE POLICY tenant_isolation_write ON access_audit_log
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

        CREATE POLICY auditor_read_all ON access_audit_log
        FOR SELECT
        TO auditor_role
        USING (true);
    """)


def downgrade() -> None:
    # 1. Drop RLS policies
    op.execute("DROP POLICY IF EXISTS auditor_read_all ON access_audit_log;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_write ON access_audit_log;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_select ON access_audit_log;")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_write ON catalog_recommendations;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_select ON catalog_recommendations;")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_write ON catalog_items;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_select ON catalog_items;")

    # 2. Disable RLS
    op.execute("ALTER TABLE access_audit_log NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE access_audit_log DISABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE catalog_recommendations NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE catalog_recommendations DISABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE catalog_items NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE catalog_items DISABLE ROW LEVEL SECURITY;")

    # 3. Drop tables
    op.drop_table("access_audit_log")
    op.drop_table("catalog_recommendations")
    op.drop_table("catalog_items")
    op.drop_table("tenants")
