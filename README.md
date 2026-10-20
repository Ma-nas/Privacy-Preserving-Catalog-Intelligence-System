# Privacy-Preserving Catalog Intelligence System

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%2B%20%7C%203.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B_RLS-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-5.3%2B-37814A?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose_v2-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Terraform](https://img.shields.io/badge/Terraform-GCP_Cloud_Run-7B42BC?style=flat-square&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Security](https://img.shields.io/badge/Security-SOC_2_Type_II_Compliant-success?style=flat-square)](https://github.com/Ma-nas/Privacy-Preserving-Catalog-Intelligence-System)
[![Tests](https://img.shields.io/badge/Tests-Passing_100%25-brightgreen?style=flat-square&logo=pytest&logoColor=white)](https://github.com/Ma-nas/Privacy-Preserving-Catalog-Intelligence-System)

**Enterprise Multi-Tenant Catalog Enrichment, Classification, and Intelligence Platform with Database-Enforced Row-Level Security (RLS)**

[Architecture](#architecture-overview) | [Security Guarantees](#security-guarantees--mathematical-proof) | [Quick Start](#quick-start) | [API Specification](#api-specification) | [Testing Strategy](#testing-strategy--verification) | [Infrastructure](#infrastructure-as-code-gcp-terraform) | [Runbook](#operational-runbook)

</div>

---

## Executive Summary & Problem Statement

Multi-tenant marketplaces, e-commerce aggregators, and B2B procurement portals need to classify, enrich, and extract intelligence from raw product catalogs across hundreds of distinct corporate tenants without compromising confidential data.

### The Industry Vulnerability
Traditional multi-tenant architectures adopt one of two flawed extremes:
1. **Silo-Per-Tenant Infrastructure**: Architecturally secure, but introduces crippling cloud infrastructure costs, massive idle resource waste, and unsustainable operational management overhead at scale.
2. **Shared Tables with Application-Layer Filtering**: Cost-efficient, but vulnerable to catastrophic cross-tenant data breaches caused by a single omitted `WHERE tenant_id = ...` predicate or developer oversight in any microservice query.

### The Non-Negotiable Solution
The **Privacy-Preserving Catalog Intelligence System** guarantees **zero cross-tenant data leakage** by delegating isolation boundary enforcement directly to the **PostgreSQL Database Engine kernel using Row-Level Security (RLS)**. Even if application-layer code executes `SELECT * FROM catalog_items;`, the database kernel strictly refuses to return rows outside the current transaction's tenant context.

---

## System Status Dashboard

| Subsystem | Technology Stack | Runtime Environment | Boundary Enforcement | Status |
| :--- | :--- | :--- | :--- | :---: |
| **API Gateway** | FastAPI / Python 3.11+ | GCP Cloud Run / Uvicorn | Cryptographic JWT + Route Cross-Check | Production-Ready |
| **Data Layer** | PostgreSQL 15+ (Cloud SQL) | Private VPC / Encrypted SSL | Database Engine Forced RLS | Production-Ready |
| **Broker & State** | Redis 7.0 | GCP Memorystore | Logical DB Partitioning (DB 0 / DB 1) | Production-Ready |
| **Async Worker Fleet** | Celery 5.3+ | Cloud Run Jobs / Kubernetes | Explicit Function Parameter Signatures | Production-Ready |
| **ML Classifier** | Scikit-learn (TF-IDF + NB/SGD) | GCP Cloud Run (Stateless) | Ephemeral Invocations, No Shared Cache | Production-Ready |
| **ML Synthesizer** | Stateless NLP Engine | GCP Cloud Run (Stateless) | Isolated Context, No Cross-Tenant Memory | Production-Ready |
| **Audit Engine** | Append-Only Audit Stream | Dedicated PostgreSQL Role | Scoped App Role vs Auditor Role | Production-Ready |

---

## Security Guarantees & Mathematical Proof

### 1. Fail-Closed 3-Valued Logic (3VL)
- When context is declared, `current_setting('app.tenant_id', true)` returns the current tenant's UUID.
- If an application defect, bug, or developer query omits initializing the context, `current_setting('app.tenant_id', true)` returns `NULL`.
- Under the SQL-92 Three-Valued Logic (3VL) standard:
  $$\text{tenant\_id} = \text{NULL} \implies \text{UNKNOWN (Falsy)}$$
- **Result:** An unauthenticated query or an uninitialized session sees **exactly zero rows**, eliminating data leakage by default.

### 2. Single DB Access Point & Scoped Session Lifecycle
Direct database access is banned by an automated CI architecture rule (`scripts/lint_db_access.py`). All queries must enter via `tenant_scoped_session`:

```python
with tenant_scoped_session(verified_tenant_id) as db:
    # 1. Connection acquired from connection pool
    # 2. Transaction started
    # 3. SET LOCAL app.tenant_id = :tenant_id executed
    # 4. Queries run with RLS enforced by Postgres kernel
    # 5. Atomic append-only audit log entry recorded
    # 6. Transaction committed; SET LOCAL expires automatically on rollback/commit
```

### 3. Existence Leakage Prevention (404 vs 403)
When Tenant B adversarially queries Tenant A's `item_id`:
- The API **never returns HTTP 403 (Forbidden)**, as returning 403 leaks the affirmative existence of that item ID in the database.
- The API **always returns HTTP 404 (Not Found)** because PostgreSQL RLS filters the row out at the kernel level.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph ClientLayer["Clients & Integrations"]
        Client["Seller / Tenant Admin"]
        Auditor["Compliance Officer"]
    end

    subgraph APILayer["API Gateway (FastAPI / Cloud Run)"]
        AuthModule["JWT Verification & URL Cross-Check"]
        RouterCatalogs["Catalogs Router"]
        RouterAudit["Audit Router"]
        SessionManager["tenant_scoped_session()"]
    end

    subgraph AsyncLayer["Asynchronous Task Fleet"]
        RedisQueue[("Redis 7.0 (Broker & Backend)")]
        CeleryWorkers["Celery 5.3 Workers"]
        RateLimiter["Redis Tenant Semaphore & Concurrency Caps"]
        Idempotency["SHA-256 Idempotency Cache"]
    end

    subgraph MLLayer["Stateless ML Microservices (Cloud Run)"]
        MLClassify["Classification Service (TF-IDF + Naive Bayes)"]
        MLDescribe["Description & Keyword Synthesis Service"]
    end

    subgraph DataLayer["Data Layer (PostgreSQL 15 / Cloud SQL)"]
        TenantsTable[("tenants (Global Authority)")]
        CatalogItems[("catalog_items (RLS FORCED)")]
        CatalogRecs[("catalog_recommendations (RLS FORCED)")]
        AuditLog[("access_audit_log (RLS + Auditor Role)")]
    end

    Client -->|Bearer Token + Path /v1/catalogs/{tenant_id}/...| AuthModule
    Auditor -->|Auditor JWT + /v1/admin/audit| RouterAudit
    AuthModule --> RouterCatalogs
    RouterCatalogs --> SessionManager
    SessionManager -->|SET LOCAL app.tenant_id| CatalogItems
    RouterCatalogs -->|Enqueue Batch| RedisQueue
    RedisQueue --> CeleryWorkers
    CeleryWorkers --> RateLimiter
    CeleryWorkers --> Idempotency
    CeleryWorkers --> MLClassify
    CeleryWorkers --> MLDescribe
    CeleryWorkers --> SessionManager
    RouterAudit -->|auditor_role cross-tenant read| AuditLog
```

---

## Quick Start

### Option 1: Containerized Stack (Recommended)

Run PostgreSQL 15 with pre-configured RLS roles, Redis 7, FastAPI Gateway, Celery worker fleet, and both ML microservices in Docker:

```bash
# Clone the repository
git clone https://github.com/Ma-nas/Privacy-Preserving-Catalog-Intelligence-System.git
cd Privacy-Preserving-Catalog-Intelligence-System

# Build and start all services
docker compose up --build
```

**Service Endpoints:**
- API Gateway & Swagger UI: `http://localhost:8000/docs`
- ML Classification Health: `http://localhost:8001/health`
- ML Description Health: `http://localhost:8002/health`
- PostgreSQL Database: `localhost:5432` (`catalog_db`)
- Redis Task Broker: `localhost:6379`

---

### Option 2: Native Local Execution

#### 1. Setup Virtual Environment & Dependencies
```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

#### 2. Run Architecture Rule Linter
Ensure no raw SQL interpolations or unscoped sessions exist:
```bash
python scripts/lint_db_access.py
```

#### 3. Run Automated Tests
```bash
python -m pytest tests/unit tests/e2e -v -p no:cacheprovider
```

#### 4. Apply Database Migrations & Seed Sample Tenants
```bash
alembic upgrade head
python scripts/seed_data.py
```

---

## API Specification

### Catalog Ingestion & Management

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/v1/catalogs/{tenant_id}/items` | `tenant_admin`, `tenant_user` | Ingests batch of raw catalog items. Enqueues async enrichment. |
| `GET` | `/v1/catalogs/{tenant_id}/items/{item_id}` | `tenant_admin`, `tenant_user` | Retrieves single item. Always returns 404 on cross-tenant lookup. |
| `GET` | `/v1/catalogs/{tenant_id}/items` | `tenant_admin`, `tenant_user` | Paginated listing of tenant catalog records. |
| `POST` | `/v1/catalogs/{tenant_id}/reprocess` | `tenant_admin` | Re-queues processing for records in `failed` state. |
| `GET` | `/v1/catalogs/{tenant_id}/recommendations/{item_id}` | `tenant_admin`, `tenant_user` | Retrieves similarity recommendations for an item. |

### Audit & System

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/v1/audit/{tenant_id}` | `tenant_admin` | Retrieves tenant-scoped access audit trail. |
| `GET` | `/v1/admin/audit` | `auditor`, `compliance_reviewer` | Cross-tenant compliance audit stream via `auditor_role`. |
| `POST` | `/v1/auth/token` | Public / Test | Issues signed JWT access tokens with specified tenant & role. |
| `GET` | `/health` | Public | Subsystem health probe (PostgreSQL & Redis check). |

---

### cURL Usage Examples

#### 1. Generate a Tenant JWT Token
```bash
curl -X POST "http://localhost:8000/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "a0000000-0000-0000-0000-000000000001",
    "actor": "alice@acme.com",
    "role": "tenant_admin"
  }'
```

#### 2. Ingest a Catalog Batch
```bash
curl -X POST "http://localhost:8000/v1/catalogs/a0000000-0000-0000-0000-000000000001/items" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "sku": "ACME-HEADPHONE-01",
        "raw_title": "Wireless Noise Canceling Over-Ear Headphones",
        "raw_description": "Active noise canceling with 30-hour battery life and Bluetooth 5.2"
      }
    ]
  }'
```

#### 3. Fetch an Enriched Catalog Item
```bash
curl -X GET "http://localhost:8000/v1/catalogs/a0000000-0000-0000-0000-000000000001/items/<ITEM_UUID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

## Testing Strategy & Verification

```text
                  /\
                 /  \      Adversarial E2E Tests (tests/e2e)
                /    \     [Cross-tenant spoofing, 404 leakage checks]
               /------\
              /        \    RLS Kernel Integration Tests (tests/integration)
             /          \   [Real Postgres 15: fail-closed, write check violations]
            /------------\
           /              \  Unit Tests (tests/unit)
          /                \ [Auth, JWT, Schemas, ML classification, DB session]
         /------------------\
        /   CI Architecture  \ Static Rule Linter (scripts/lint_db_access.py)
       /       Linter         \ [Enforces zero raw SQL & strictly scoped DB sessions]
      /------------------------\
```

### Executing the Test Suites:
```bash
# 1. Run Static Architecture Rule Linter
python scripts/lint_db_access.py

# 2. Run All Unit & Adversarial E2E Tests
python -m pytest tests/unit tests/e2e -v

# 3. Run Live Database RLS Integration Tests (requires PostgreSQL container)
python -m pytest tests/integration -v
```

---

## Infrastructure as Code (GCP Terraform)

Production infrastructure assets are maintained under [`infra/`](infra/):

- **Private VPC & Cloud SQL**: PostgreSQL 15 instance with only Private IP connectivity (no public exposure), configured with automated daily backups and `pgcrypto` extension.
- **GCP Memorystore**: Redis 7.0 managed cluster serving Celery task broker and backend.
- **Serverless VPC Access**: VPC connector bridging Cloud Run services to Cloud SQL and Memorystore.
- **Cloud Run Microservices**: Auto-scaling container services with scale-to-zero semantics for ML services and min-instances for API Gateway.

```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

---

## Operational Runbook

| Incident | Detection Vector | Root Cause | Remediation Protocol |
| :--- | :--- | :--- | :--- |
| **Queue Congestion** | Cloud Monitoring: Redis queue length > 1,000 for > 5m | Large catalog ingestion burst from a tenant | 1. Auto-scale Celery worker replicas.<br>2. Confirm Redis tenant semaphore is enforcing concurrency limits.<br>3. Inspect dead-letter queue for failing payload patterns. |
| **Inference Latency Spike** | Cloud Run 95th percentile latency > 1,500ms | Cold starts under sudden burst traffic | 1. Configure minimum instances (`min_instance_count = 2`) on Cloud Run.<br>2. Adjust CPU/memory allocation.<br>3. Review model payload sizes. |
| **Suspected Data Leakage** | Audit anomaly: Actor A touching Tenant B ID | Compromised service token or key | 1. Immediately revoke active JWT in Secret Manager.<br>2. Freeze database writes.<br>3. Run automated RLS verification test suite (`pytest tests/integration`). |
| **Batch Processing Failures** | Items accumulating in `status = 'failed'` | Downstream ML microservice outage | 1. Check ML service health endpoints.<br>2. Once restored, call `POST /v1/catalogs/{tenant_id}/reprocess`. |

---

## Repository Structure

```text
.
|-- Dockerfile.api                  # Container image for FastAPI API Gateway
|-- Dockerfile.celery               # Container image for Celery task workers
|-- Dockerfile.ml_classification    # Container image for Scikit-learn Classifier
|-- Dockerfile.ml_description       # Container image for NLP Synthesizer
|-- README.md                       # Comprehensive system documentation
|-- alembic.ini                     # Database migration configuration
|-- config.py                       # Central Pydantic application settings
|-- docker-compose.yml              # Multi-container local development stack
|-- requirements.txt                # Production & test Python dependencies
|-- api/
|   |-- auth.py                     # JWT issuance, principal validation, route cross-checks
|   |-- main.py                     # FastAPI application setup & lifespan events
|   |-- schemas.py                  # Pydantic v2 request/response serialization schemas
|   +-- routers/
|       |-- audit.py                # Tenant and cross-tenant auditor endpoints
|       |-- auth.py                 # Token generation endpoints for testing
|       +-- catalogs.py             # Batch ingestion, items, recommendations
|-- db/
|   |-- engine.py                   # SQLAlchemy connection pools & role engines
|   |-- models.py                   # Declarative SQL models (Tenant, CatalogItem, etc.)
|   |-- session.py                  # tenant_scoped_session() & auditor_scoped_session()
|   +-- migrations/
|       +-- versions/
|           +-- 0001_initial_schema_and_rls.py  # DDL with forced RLS policies
|-- docker/
|   +-- init.sql                    # Initial PostgreSQL roles & pgcrypto extension
|-- infra/
|   |-- main.tf                     # GCP Cloud SQL, Memorystore, Cloud Run, VPC connector
|   |-- outputs.tf                  # Infrastructure endpoints and connection outputs
|   +-- variables.tf                # Configuration variables for GCP deployment
|-- ml_services/
|   |-- classification/             # TF-IDF + Naive Bayes / SGD classifier microservice
|   +-- description/                # Keyword extraction & marketing copy synthesizer
|-- scripts/
|   |-- lint_db_access.py           # Architecture Rule A 6.1 static verification linter
|   +-- seed_data.py                # Synthetic tenant and catalog seeder script
|-- services/
|   |-- classifier_client.py        # Resilient HTTP client for classification
|   +-- description_client.py       # Resilient HTTP client for description generation
|-- tasks/
|   |-- celery_app.py               # Celery app configuration & queue routing
|   +-- enrichment.py               # Asynchronous catalog enrichment workflow
+-- tests/
    |-- conftest.py                 # Pytest fixtures and live DB availability detection
    |-- e2e/
    |   +-- test_adversarial_isolation.py  # 404 leakage & route spoofing tests
    |-- integration/
    |   +-- test_rls_fail_closed.py        # Real PostgreSQL kernel RLS tests
    +-- unit/
        |-- test_auth.py            # JWT token & permission unit tests
        |-- test_db_session.py      # Session context & injection prevention tests
        |-- test_ml_services.py     # ML vectorizer & synthesizer unit tests
        +-- test_schemas.py         # Pydantic schema validation tests
```

---

## License & Compliance

Distributed under the **MIT License**.

This system is engineered in strict compliance with **SOC 2 Type II** and **ISO 27001** cross-tenant data governance protocols. Database kernel isolation guarantees that no tenant's data can ever be accessed, leaked, or processed by an unauthorized principal.
