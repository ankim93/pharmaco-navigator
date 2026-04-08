# Backend - Pharmaco-Navigator

FastAPI backend for the Pharmaco-Navigator Clinical Decision Support system. Handles SMART on FHIR OAuth 2.0 authentication, FHIR data retrieval, pharmacogenomic screening, and Traffic Light alert generation.

See [SETUP.md](../SETUP.md) at the repository root for full installation instructions.

---

## Table of Contents

- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Service Layer](#service-layer)
- [Data Models](#data-models)
- [Configuration](#configuration)
- [Database Seeding](#database-seeding)
- [Running the Server](#running-the-server)
- [Testing](#testing)

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI app instance, router registration, lifespan
│   ├── api/
│   │   ├── deps.py                 # Shared FastAPI dependencies (session extraction, DB session)
│   │   └── v1/
│   │       ├── auth.py             # SMART on FHIR OAuth 2.0 flow
│   │       ├── fhir.py             # FHIR patient and medication endpoints
│   │       ├── patient.py          # Genomic profile summary endpoint
│   │       └── alerts.py           # Traffic Light alert generation endpoint
│   ├── core/
│   │   ├── config.py               # Pydantic Settings — loads from backend/.env
│   │   ├── cpic_tables.py          # CPIC pharmacogenomic reference tables
│   │   ├── fallback_guidelines.py  # Local CPIC guideline cache (used when CPIC API is down)
│   │   └── session.py              # BFF session helpers (type-safe session value accessors)
│   ├── db/
│   │   └── session.py              # SQLAlchemy async engine, session factory
│   ├── models/
│   │   ├── genotype.py             # SQLAlchemy ORM model for the genotypes table
│   │   ├── recommendation.py       # Pydantic model for recommendation payload
│   │   └── schemas.py              # Shared Pydantic request/response schemas
│   └── services/
│       ├── fhir_service.py         # Retrieves Patient and MedicationRequest from Cerner FHIR R4
│       ├── demo_fhir_service.py    # Returns synthetic FHIR data for offline demo patients
│       ├── genomic_service.py      # Queries genotypes table in PostgreSQL
│       ├── phenotype_service.py    # Activity Score algorithm -> metabolizer status phenotype
│       ├── recommendation_service.py  # Orchestrates alert generation pipeline
│       ├── cpic_service.py         # Calls CPIC API; falls back to local cache on failure
│       └── rxnav_service.py        # Resolves drug name to RxNorm RxCUI via RxNav API
├── db/
│   ├── insert_cerner_patients.py   # Seeds 9 Cerner sandbox patient genotypes
│   ├── insert_demo_patients.sql    # Seeds DEMO001–DEMO006 patient genotypes
│   ├── reset_db.sql                # Drops and recreates the genotypes table
│   └── run_sql.py                  # Utility: executes a .sql file against the configured database
├── tests/
│   ├── unit/                       # Pure unit tests (no I/O, all dependencies mocked)
│   ├── api/                        # API tests using FastAPI TestClient
│   ├── integration/                # Integration tests (require live database and API credentials)
│   └── e2e/                        # End-to-end Cerner FHIR flow tests
├── requirements.txt
└── pytest.ini
```

---

## API Reference

All routes are prefixed with `/api/v1`. The interactive Swagger UI is available at `http://localhost:8000/docs` when the server is running.

### Authentication (`/api/v1/auth`)

| Method | Path | Auth Required | Description |
|--------|------|:-------------:|-------------|
| GET | `/auth/launch` | No | Entry point for SMART on FHIR EHR launch. Validates `iss` and `launch` parameters, constructs the authorization URL, stores a cryptographic `state` value in session, and redirects the browser to the Cerner authorization server. |
| GET | `/auth/callback` | No | Receives the authorization code from Cerner after the clinician approves access. Verifies the `state` parameter, exchanges the code for access and ID tokens, extracts the patient context, and creates a server-side session. Returns a redirect to the frontend application. |
| POST | `/auth/logout` | Yes | Clears the server-side session and deletes the session cookie. Idempotent - safe to call on already-expired sessions. |
| GET | `/auth/session` | Yes | Returns the current session status including patient ID and session expiry. Used by the frontend to verify authentication state on page load. |

### FHIR Resources (`/api/v1/fhir`)

| Method | Path | Auth Required | Description |
|--------|------|:-------------:|-------------|
| GET | `/fhir/patient` | Yes | Fetches the FHIR `Patient` resource for the session's patient from Cerner FHIR R4. Returns structured demographics: name, birth date, gender, and identifiers. For demo patients, returns data from `demo_fhir_service`. |
| GET | `/fhir/medications` | Yes | Fetches active `MedicationRequest` resources for the patient. Each medication is normalized via the RxNav API to obtain an RxCUI. Returns a list of medication objects with display name and RxCUI. |

### Clinical Insights (`/api/v1/patient`)

| Method | Path | Auth Required | Description |
|--------|------|:-------------:|-------------|
| GET | `/patient/{patient_id}/summary` | Yes | Returns the patient's complete genomic profile: all diplotypes stored in the database, their translated phenotypes, and the set of genes with and without data. |
| GET | `/patient/{patient_id}/alerts` | Yes | Runs the full pharmacogenomic screening pipeline. Retrieves medications, resolves RxCUIs, looks up genotypes, translates phenotypes, queries CPIC (or fallback cache), and returns a structured alert set classified as RED / YELLOW / GREEN / GREY. |

### System

| Method | Path | Auth Required | Description |
|--------|------|:-------------:|-------------|
| GET | `/health` | No | Returns health status of the database connection and CPIC API reachability. Used by load balancers and monitoring. |
| GET | `/docs` | No | Swagger UI - interactive API documentation. |
| GET | `/redoc` | No | ReDoc - alternative API documentation viewer. |

---

## Service Layer

### `fhir_service.py`

Calls the Cerner FHIR R4 API using the access token stored in the session. Handles FHIR bundle pagination for `MedicationRequest` searches. Raises `HTTPException(404)` if the patient is not found and `HTTPException(503)` on Cerner API errors.

### `demo_fhir_service.py`

Returns hard-coded synthetic FHIR `Patient` and `MedicationRequest` data for patients `DEMO001` through `DEMO007`. Used for offline development and testing without Cerner credentials. `DEMO007` intentionally has no genomic data in the database - it tests the missing-data GREY alert path. The `DEMO_MEDICATIONS` dictionary in this file defines the synthetic medication list for each demo patient and serves as the canonical contract for demo test assertions.

### `genomic_service.py`

Executes async SQLAlchemy queries against the `genotypes` table. Returns all diplotype rows for a given `patient_id`, indexed lookup on `(patient_id, gene_symbol)`. Returns an empty list (not an error) if no genotype data exists - the recommendation layer interprets this as a GREY alert.

### `phenotype_service.py`

Translates star-allele genotypes to standardized CPIC phenotypes using two methods depending on gene type, dispatched via the `GENE_PHENOTYPE_FUNCTIONS` registry in `cpic_tables.py`:

**Metabolic enzymes - Activity Score (CYP2D6, CYP2C19)**

1. Splits the diplotype string (e.g., `*1/*4`) into two alleles.
2. Looks up each allele in a per-gene function value table (`*1` = 1.0, `*4` = 0.0, etc.).
3. Sums the two values to produce an Activity Score.
4. Maps the score to a metabolizer status: Poor (0), Intermediate (0.5–1.0), Normal (1.5–2.0), Rapid (2.5), Ultrarapid (>2.5).

Unknown alleles default to Normal Function (1.0) with a warning logged. Transporters return `None` from `calculate_score()` — no Activity Score is computed for them.

**Transporters - Direct diplotype mapping (SLCO1B1, ABCB1)**

The diplotype (or SNP genotype) is passed directly to a CPIC lookup table that returns a functional status label (e.g., Normal Function, Decreased Function, Poor Function) without computing an Activity Score.

### `recommendation_service.py`

Orchestrates the full alert pipeline for a single patient:

1. Calls `genomic_service` to retrieve all diplotypes.
2. For each diplotype, calls `phenotype_service` to get the metabolizer status.
3. Calls `fhir_service` (or `demo_fhir_service`) to get active medications.
4. For each medication, calls `rxnav_service` to normalize to an RxCUI.
5. For each (medication RxCUI, gene phenotype) pair, calls `cpic_service` for the guideline recommendation.
6. Classifies each recommendation as RED / YELLOW / GREEN / GREY.
7. Returns the complete structured alert payload.

If a patient has no genomic data, returns GREY alerts for all medications.

### `cpic_service.py`

Queries `GET https://api.cpicpgx.org/v1/recommendation?rxcui=<id>&phenotype=<label>`. On HTTP error or timeout, transparently falls back to `fallback_guidelines.py`. Fallback use is written to the application log at WARNING level for audit purposes. Returns `None` (no guideline found) rather than raising an exception when a drug-gene pair has no CPIC recommendation.

### `rxnav_service.py`

Calls the NLM RxNav REST API `GET /approximateTerm.json?term=<drug_name>` to resolve a free-text drug name to a canonical RxCUI. Returns the best-match RxCUI, or `None` if no match is found. A `None` RxCUI causes the medication to be skipped in CPIC lookup with a GREY alert indicating insufficient data.

---

## Data Models

### `genotypes` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Auto-increment row identifier |
| `patient_id` | VARCHAR(255) NOT NULL | Patient identifier (Cerner FHIR ID or DEMO001–DEMO007) |
| `gene_symbol` | VARCHAR(50) NOT NULL | Pharmacogene symbol (e.g., CYP2D6, CYP2C19) |
| `allele_1` | VARCHAR(50) NOT NULL | First star allele (e.g., *1) |
| `allele_2` | VARCHAR(50) NOT NULL | Second star allele (e.g., *4) |
| `diplotype` | VARCHAR(100) | Composite diplotype string (e.g., *1/*4) |
| `activity_score` | FLOAT | Precomputed Activity Score |
| `phenotype` | VARCHAR(100) | Precomputed phenotype label |
| `created_at` / `updated_at` | TIMESTAMP | Audit timestamps |

Indexes: `idx_genotypes_patient_id` (patient_id), `idx_genotypes_gene_symbol` (gene_symbol).

### Pydantic schemas

| Schema | File | Description |
|--------|------|-------------|
| `AlertResponse` | `schemas.py` | Top-level response for `/patient/{id}/alerts`; contains lists of RED/YELLOW/GREEN/GREY alerts |
| `AlertItem` | `schemas.py` | Single alert: drug name, gene, phenotype, recommendation text, evidence level |
| `PatientSummary` | `schemas.py` | Genomic profile summary with diplotype list and missing-gene list |
| `GenotypeRecord` | `genotype.py` | ORM model mirroring the `genotypes` table |
| `RecommendationPayload` | `recommendation.py` | Internal service-layer model for CPIC recommendation data |

---

## Configuration

All settings are loaded from `backend/.env` by `app/core/config.py` using Pydantic `BaseSettings`.

| Variable | Required | Description |
|----------|:--------:|-------------|
| `PROJECT_NAME` | No | Application display name (default: `Pharmaco-Navigator`) |
| `ENVIRONMENT` | No | `development` or `production` |
| `SECRET_KEY` | **Yes** | 256-bit secret for session signing; generate with `openssl rand -hex 32` |
| `ALLOWED_ORIGINS` | **Yes** | Comma-separated CORS origin list (e.g., `http://localhost:3000`) |
| `DATABASE_URL` | **Yes** | SQLAlchemy async URL: `postgresql+asyncpg://user:password@host/db?ssl=require` |
| `DATABASE_POOL_SIZE` | No | Connection pool size (default: 20) |
| `DATABASE_MAX_OVERFLOW` | No | Max overflow connections above pool size (default: 10) |
| `CERNER_CLIENT_ID` | **Yes** | SMART on FHIR client ID from Cerner developer portal |
| `CERNER_CLIENT_SECRET` | **Yes** | SMART on FHIR client secret |
| `CERNER_REDIRECT_URI` | **Yes** | Must match the registered redirect URI exactly |
| `CERNER_FHIR_BASE_URL` | **Yes** | Cerner FHIR R4 base URL including tenant ID |
| `CERNER_OAUTH_AUTHORIZE_URL` | **Yes** | Cerner authorization endpoint |
| `CERNER_OAUTH_TOKEN_URL` | **Yes** | Cerner token endpoint |
| `RXNAV_BASE_URL` | No | RxNav API base URL (default: `https://rxnav.nlm.nih.gov/REST`) |
| `CPIC_API_BASE_URL` | No | CPIC API base URL (default: `https://api.cpicpgx.org/v1`) |
| `LOG_LEVEL` | No | Python logging level (default: `INFO`) |

For demo mode (no Cerner credentials), `CERNER_*` variables are still required by the settings validator but are not called during demo patient requests; any non-empty placeholder values will satisfy validation.

---

## Database Seeding

### Demo patients (DEMO001–DEMO007)

```bash
cd backend
.venv\Scripts\activate

# Run SQL seed file
python db/run_sql.py db/insert_demo_patients.sql
```

`DEMO007` is intentionally absent from the seed file - it represents a patient with no genomic data on file, which exercises the GREY alert pathway in tests.

### Cerner sandbox patients

```bash
python db/insert_cerner_patients.py
```

This script uses the `DATABASE_URL` from your `.env` to insert genotypes for 9 real Cerner sandbox patient identifiers. The patient IDs are the authoritative source for which Cerner sandbox patients are supported.

---

## Running the Server

```bash
cd backend
.venv\Scripts\activate

# Development
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Swagger UI at `http://localhost:8000/docs`.

---

## Testing

Tests are organized in `backend/tests/` and configured in `pytest.ini`.

```bash
cd backend
.venv\Scripts\activate

# Unit + API tests: no external connections
pytest tests/unit -v
pytest tests/api -v

# Integration tests (require live database)
pytest tests/integration -v

# E2E tests against Cerner sandbox (require valid SMART credentials)
pytest tests/e2e -v
```

**Test markers** (defined in `pytest.ini`):

| Marker | Scope | External I/O |
|--------|-------|:------------:|
| `unit` | Individual service functions | None (all mocked) |
| `api` | FastAPI endpoint tests via TestClient | None (services mocked) |
| `integration` | Database integration | PostgreSQL required |
| `e2e` | Full pipeline tests | Cerner + PostgreSQL required |

