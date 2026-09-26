# Privacy-Preserving Catalog Intelligence System
### Enterprise Multi-Tenant Catalog Enrichment and Intelligence Platform

---

## Executive Summary & System Dashboard

The **Privacy-Preserving Catalog Intelligence System** is an enterprise data enrichment and classification platform engineered specifically for multi-tenant marketplaces, B2B procurement portals, and e-commerce aggregators. 

The platform guarantees absolute tenant data isolation by delegating tenant boundary enforcement directly to the **PostgreSQL Database Engine via Row-Level Security (RLS)**, eliminating reliance on error-prone application-layer query filtering.

### System Status Dashboard

| Subsystem | Technology Stack | Runtime Environment | Isolation Enforcement | Operational Status |
| :--- | :--- | :--- | :--- | :--- |
| **API Gateway** | FastAPI / Python 3.11+ | GCP Cloud Run / Uvicorn | Authenticated JWT Principal Cross-Check | Active / Production-Ready |
| **Data Layer** | PostgreSQL 15+ (Cloud SQL) | Private VPC / Encrypted SSL | Database Engine RLS (Forced) | Active / Production-Ready |
| **Task Broker & Backend** | Redis 7.0 | GCP Memorystore | Logical DB Partitioning (DB 0 / DB 1) | Active / Production-Ready |
| **Async Worker Fleet** | Celery 5.3+ | Cloud Run Jobs / Kubernetes | Explicit Function Signatures | Active / Production-Ready |
| **ML Classification** | Scikit-learn (TF-IDF + NB) | GCP Cloud Run (Stateless) | Isolated Ephemeral Invocations | Active / Production-Ready |
| **ML Content Generation** | NLP Synthesizer | GCP Cloud Run (Stateless) | No Cross-Tenant Shared Memory | Active / Production-Ready |
| **Compliance Audit** | Access Audit Engine | PostgreSQL Dedicated Role | Scoped App Role / Cross-Tenant Auditor | Active / Production-Ready |

---

## Architectural Principle: Database-Enforced Isolation

### The Problem
Traditional multi-tenant systems adopt one of two operational extremes:
1. **Silo-Per-Tenant Infrastructure**: Architecturally secure, but introduces prohibitive cloud cost and unmanageable operational overhead at scale.
2. **Shared Tables with Application Filtering**: Economically viable, but vulnerable to catastrophic data breaches caused by a single omitted `WHERE tenant_id = ...` predicate in application code.

### The Non-Negotiable Solution
This system pushes tenant boundary validation into the database engine kernel using PostgreSQL Row-Level Security (RLS). Every single database session must declare its active tenant context before executing any query:

```sql
SET LOCAL app.tenant_id = '<tenant_uuid>';
```

### Mathematical Proof of Fail-Closed Behavior
The system's RLS policies evaluate against the session variable:
```sql
CREATE POLICY tenant_isolation_select ON catalog_items
  FOR SELECT USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
```
- In PostgreSQL, `current_setting('app.tenant_id', true)` returns `NULL` if the variable has not been initialized.
- In Three-Valued Logic (3VL) SQL standard:
  $$\text{tenant\_id} = \text{NULL} \implies \text{UNKNOWN (Falsy)}$$
- As a consequence, an unauthenticated session or a programming bug that bypasses tenant context initialization sees **exactly zero rows**, completely preventing accidental data exposure.

---

## High-Level Architecture Diagram

```
                                   +--------------------------------------------------------+
                                   |                     Async Layer                        |
                                   |                                                        |
+-----------------+  POST / GET    |  +-----------------------+   +----------------------+  |
|  Client / Admin | -------------> |  | Redis (Broker/Backend)| ->| Celery Workers       |  |
+-----------------+                |  +-----------------------+   +----------+-----------+  |
         |                         +-----------------------------------------|--------------+
         |                                                                   |
         v                                                                   |
+-------------------------------+                                            |
| API Layer (FastAPI)           |                                            |
| - JWT Principal Validation    |                                            |
| - Tenant Route Cross-Check    | -- SET LOCAL app.tenant_id --+             |
| - tenant_scoped_session       |                              |             |
+---------------+---------------+                              |             |
                |                                              v             v
                |                                     +-------------------------------------+
                |                                     | Data Layer (Cloud SQL PostgreSQL 15)|
                |                                     | - catalog_items (RLS FORCED)        |
                |                                     | - catalog_recommendations (RLS)     |
                |                                     | - access_audit_log (RLS + Auditor)  |
                |                                     +-------------------------------------+
                v                                                       ^
+-----------------------------------------------+                       |
| ML Layer (Stateless Cloud Run Services)       |                       |
| - Classification Service (Scikit-Learn TF-IDF)|                       |
| - Description Generation & Recommendation     | ----------------------+
+-----------------------------------------------+
```

---

## Anti-Gravity Architecture Compliance Matrix

| Architecture Requirement | Implementation Detail | Source File Reference | Verification Method |
| :--- | :--- | :--- | :--- |
| **No Raw SQL Interpolation** | Parameterized query compilation via SQLAlchemy 2.0 | `db/session.py` | Static code analysis |
| **Single DB Access Point** | Mandatory `tenant_scoped_session()` wrapper | `db/session.py` | Automated CI Linter (`scripts/lint_db_access.py`) |
| **Forced RLS Coverage** | `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` | `db/migrations/versions/0001_initial_schema_and_rls.py` | Integration test suite |
| **Explicit Celery Task Signatures** | `tenant_id` passed as explicit function parameter | `tasks/enrichment.py` | Unit and integration test suite |
| **URL Parameter Verification** | JWT claims cross-referenced against path `tenant_id` | `api/auth.py` | Adversarial test suite |
| **Information Leakage Prevention** | Cross-tenant item queries return HTTP 404 (never 403) | `api/routers/catalogs.py` | `tests/e2e/test_adversarial_isolation.py` |
| **Reversible Schema Migrations** | Complete `upgrade()` and `downgrade()` routines | `db/migrations/` | Alembic migration dry-runs |
| **Append-Only Auditing** | Atomic audit row write within the mutating transaction | `db/session.py` | Functional verification tests |

---

## Core Service Catalog

### 1. API Gateway (`api/`)
- Built on FastAPI with asynchronous request handling.
- Validates bearer tokens using cryptographic JWT verification (`HS256`/`RS256`).
- Routes incoming catalog batches into the asynchronous task queue.
- Exposes tenant-specific read/write endpoints and cross-tenant compliance audit endpoints.

### 2. Database & RLS Engine (`db/`)
- **`tenants`**: Identity authority table (global lookup, not RLS restricted).
- **`catalog_items`**: Primary catalog entity holding raw input, enrichment state, category taxonomy, and generated descriptions.
- **`catalog_recommendations`**: Item-to-item similarity associations within tenant boundaries.
- **`access_audit_log`**: Structured audit log tracking actor, action, resource, and timestamp.
- **`db/session.py`**: The single sanctioned interface for session instantiation in the codebase.

### 3. Asynchronous Pipeline (`tasks/`)
- Powered by Celery and Redis.
- Dedicated queue routing across `classification`, `description`, `reindex`, and `default` queues.
- Redis-backed rate limiting and concurrency semaphores per tenant.
- Cryptographic SHA-256 idempotency cache preventing duplicate ML inference costs.

### 4. Machine Learning Microservices (`ml_services/`)
- **Classification Engine**: Stateless microservice utilizing TF-IDF vectorization and Multinomial Naive Bayes / SGD classification.
- **Description & Recommendation Engine**: Stateless synthesizer generating structured marketing copy and extracting product feature tags.
- Compliant with Cloud Run scale-to-zero semantics and strict absence of cross-tenant caching.

---

## API Specification Summary

### Catalog Management Endpoints

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/v1/catalogs/{tenant_id}/items` | `tenant_admin`, `tenant_user` | Batch ingestion of raw catalog items. Enqueues async enrichment. |
| `GET` | `/v1/catalogs/{tenant_id}/items/{item_id}` | `tenant_admin`, `tenant_user` | Retrieves single item. Returns 404 on cross-tenant lookup. |
| `GET` | `/v1/catalogs/{tenant_id}/items` | `tenant_admin`, `tenant_user` | Paginated listing of tenant catalog records. |
| `POST` | `/v1/catalogs/{tenant_id}/reprocess` | `tenant_admin` | Re-enqueues processing for items in `failed` state. |
| `GET` | `/v1/catalogs/{tenant_id}/recommendations/{item_id}` | `tenant_admin`, `tenant_user` | Retrieves similarity recommendations for an item. |

### Audit & Security Endpoints

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/v1/audit/{tenant_id}` | `tenant_admin` | Retrieves tenant-scoped access audit history. |
| `GET` | `/v1/admin/audit` | `auditor`, `compliance_reviewer` | Cross-tenant compliance audit stream via `auditor_role`. |
| `POST` | `/v1/auth/token` | Public / Test | Issues signed JWT access tokens for testing and integration. |
| `GET` | `/health` | Public | Subsystem health probe (PostgreSQL and Redis connectivity). |

---

## Operational Runbook & Alert Response Guide

| Incident Scenario | Metric / Detection Vector | Root Cause Analysis | Remediation Protocol |
| :--- | :--- | :--- | :--- |
| **Celery Queue Congestion** | Cloud Monitoring: Redis queue length > 1,000 for > 5 min | Large catalog ingestion burst by single tenant | 1. Scale Celery worker replicas.<br>2. Verify Redis semaphore backpressure is enforcing tenant concurrency caps.<br>3. Inspect dead-letter queue for recurring execution loops. |
| **Inference Latency Spike** | Cloud Run 95th Percentile Latency > 1,500ms | Cold starts under sudden burst traffic | 1. Configure minimum instances (`min_instance_count = 2`) on Cloud Run.<br>2. Inspect CPU and RAM allocation on microservices.<br>3. Review model payload sizes. |
| **Suspected Data Leakage** | Audit Log Anomaly: Actor A touching Tenant B resource ID | Invalid credentials or compromised service token | 1. Immediately revoke active token/credentials in Secret Manager.<br>2. Suspend database writes.<br>3. Execute automated RLS verification test suite (`pytest tests/integration`). |
| **Failed Processing Batch** | Accumulation of records with `status = 'failed'` | ML service unavailability or invalid schema inputs | 1. Check microservice health endpoints.<br>2. Call `POST /v1/catalogs/{tenant_id}/reprocess` after service restoration. |

---

## Local Development & Deployment

### Method 1: Containerized Stack via Docker Compose

Execute the entire platform with PostgreSQL, Redis, API Gateway, Celery, and ML services in isolated containers:

```bash
docker-compose up --build
```

Endpoints will be accessible at:
- API Gateway Documentation: `http://localhost:8000/docs`
- Classification Microservice: `http://localhost:8001/health`
- Description Microservice: `http://localhost:8002/health`

### Method 2: Native Local Execution

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Execute Architecture Rule Linter**:
   ```bash
   python scripts/lint_db_access.py
   ```

3. **Execute Automated Test Suite**:
   ```bash
   python -m pytest tests/unit tests/e2e -v -p no:cacheprovider
   ```

4. **Seed Demonstration Data & Credentials**:
   ```bash
   python scripts/seed_data.py
   ```

---

## Infrastructure as Code (GCP Terraform)

Deployment assets are organized under `infra/`:
- **`infra/main.tf`**: Provisions Google Cloud SQL PostgreSQL 15 with Private IP, Memorystore Redis, Serverless VPC Access Connectors, and Cloud Run deployments.
- **`infra/variables.tf`**: GCP Project, region, and compute tier parameters.
- **`infra/outputs.tf`**: Service URLs, internal IP addresses, and resource identifiers.

To plan and apply infrastructure:
```bash
cd infra
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

---

## Repository Structure

```
.
|-- Dockerfile.api
|-- Dockerfile.celery
|-- Dockerfile.ml_classification
|-- Dockerfile.ml_description
|-- README.md
|-- alembic.ini
|-- api
|   |-- __init__.py
|   |-- auth.py
|   |-- main.py
|   |-- routers
|   |   |-- audit.py
|   |   |-- auth.py
|   |   `-- catalogs.py
|   `-- schemas.py
|-- config.py
|-- db
|   |-- __init__.py
|   |-- engine.py
|   |-- migrations
|   |   |-- env.py
|   |   |-- script.py.mako
|   |   `-- versions
|   |       `-- 0001_initial_schema_and_rls.py
|   |-- models.py
|   `-- session.py
|-- docker
|   `-- init.sql
|-- docker-compose.yml
|-- infra
|   |-- main.tf
|   |-- outputs.tf
|   `-- variables.tf
|-- ml_services
|   |-- classification
|   |   |-- main.py
|   |   `-- model.py
|   `-- description
|       |-- generator.py
|       `-- main.py
|-- requirements.txt
|-- scripts
|   |-- lint_db_access.py
|   `-- seed_data.py
|-- services
|   |-- __init__.py
|   |-- classifier_client.py
|   `-- description_client.py
|-- tasks
|   |-- __init__.py
|   |-- celery_app.py
|   `-- enrichment.py
`-- tests
    |-- conftest.py
    |-- e2e
    |   `-- test_adversarial_isolation.py
    |-- integration
    |   `-- test_rls_fail_closed.py
    `-- unit
        |-- test_auth.py
        |-- test_db_session.py
        |-- test_ml_services.py
        `-- test_schemas.py
```

---

## License & Compliance

Copyright (c) 2026. All rights reserved.
System architecture and implementations adhere strictly to SOC 2 Type II cross-tenant data governance protocols.
