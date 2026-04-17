# Pharmaco-Navigator

An Automated Clinical Decision Support System (CDSS) for genomic-informed medication safety.

Pharmaco-Navigator integrates with Electronic Health Records to identify potential drug-gene interactions based on patient genomic profiles. It presents clinicians with actionable, categorized safety alerts using a Traffic Light system (RED / YELLOW / GREEN / GREY) to support safer medication decisions at the point of prescribing.

See [SETUP.md](SETUP.md) for complete installation and configuration instructions.

---

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Security](#security)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Documentation](#documentation)
- [License](#license)

---

## Features

### 1. SMART on FHIR Secure Authentication

The application launches directly from a Cerner EHR using the SMART on FHIR OAuth 2.0 authorization code flow. When a clinician opens Pharmaco-Navigator from within the EHR, the launch request contains an `iss` (FHIR server URL) and a `launch` token that encodes the active patient context. The backend exchanges these for an authorization code and then for access and ID tokens.

Session state is maintained server-side using the Backend-for-Frontend (BFF) pattern. The React frontend never handles raw OAuth tokens; all token storage and refresh logic are confined to the FastAPI backend. Browser sessions are tracked via `HttpOnly`, `Secure`, `SameSite=Lax` cookies. CSRF attacks are mitigated by a cryptographically random `state` parameter verified on every callback.

### 2. Dynamic FHIR Synchronization and Normalization

After authentication, the backend immediately pulls live clinical data from the Cerner FHIR R4 API: patient demographics (`Patient` resource) and active medication orders (`MedicationRequest` resources). Drug names returned by FHIR often vary by brand, trailing dose string, or formulation. Each name is normalized by querying the NLM RxNav API to resolve a canonical RxNorm Concept Unique Identifier (RxCUI). Downstream CPIC lookups use the RxCUI to ensure consistent matching regardless of how the EHR recorded the medication.

### 3. Genomic Data Management

Patient pharmacogenomic profiles are stored in Azure PostgreSQL 14 as star-allele diplotypes (e.g., `*1/*4`, `*2/*2`). The `genotypes` table is indexed on `patient_id` and `gene_symbol` for sub-millisecond lookup during alert generation. Supported pharmacogenes include CYP2D6, CYP2C19, CYP2C9, and SLCO1B1. The seeding pipeline (`backend/db/`) loads both real Cerner sandbox patient identifiers and synthetic demo patients (DEMO001–DEMO007) used for offline testing.

### 4. Phenotype Translation Engine

Each supported pharmacogene uses one of two CPIC-defined translation methods depending on whether it is a metabolic enzyme or a membrane transporter.

---

#### Method 1: Activity Score - Metabolic Enzymes (CYP2D6, CYP2C19)

Each allele in the diplotype is assigned a numeric function score; the two scores are summed to produce an Activity Score, which is then mapped to a metabolizer status. The allele scores and phenotype thresholds are defined per gene by CPIC.

**CYP2D6 - Selected Allele Scores**

| Allele | Function | Score |
|--------|----------|-------|
| \*1, \*2 | Normal | 1.0 |
| \*17, \*41 | Decreased | 0.5 |
| \*10 | Decreased | 0.25 |
| \*4, \*5 | No Function | 0.0 |

**CYP2D6 - Activity Score to Phenotype**

| Activity Score | Phenotype |
|----------------|-----------|
| 0 | Poor Metabolizer |
| > 0 and < 1.25 | Intermediate Metabolizer |
| 1.25 – 2.25 | Normal Metabolizer |
| > 2.25 | Ultrarapid Metabolizer |

**CYP2C19 - Selected Allele Scores**

| Allele | Function | Score |
|--------|----------|-------|
| \*1, \*17 | Normal / Increased | 1.0 |
| \*2, \*3 | No Function | 0.0 |

**CYP2C19 - Activity Score to Phenotype**

| Activity Score | Phenotype |
|----------------|-----------|
| 0 | Poor Metabolizer |
| 1.0 – 1.5 | Intermediate Metabolizer |
| 2.0 | Normal Metabolizer |
| > 2.0 | Ultrarapid Metabolizer |

---

#### Method 2: Direct Diplotype Mapping - Transporters (SLCO1B1, ABCB1)

Transporters do not use an Activity Score. The diplotype (or SNP genotype) is looked up directly in a CPIC-defined mapping table to return a functional status.

**SLCO1B1 — Diplotype to Functional Status**

| Diplotype | Functional Status |
|-----------|-------------------|
| \*1/\*1 | Normal Function |
| \*1/\*5, \*1/\*15 | Decreased Function |
| \*5/\*5, \*15/\*15, \*5/\*15 | Poor Function |

**ABCB1 — Genotype (rs1045642) to Functional Status**

| Genotype | Functional Status |
|----------|-------------------|
| C/C (\*1/\*1) | Normal Transport Function |
| C/T (\*1/\*2) | Intermediate Transport Function |
| T/T (\*2/\*2) | Reduced Transport Function |

---

The resulting phenotype or functional status label is passed to the screening layer for evidence-based CPIC guideline lookup.

### 5. Evidence-Based Drug-Gene Screening

For each active medication, the backend queries the CPIC (Clinical Pharmacogenetics Implementation Consortium) API with the normalized RxCUI and the patient's phenotype. CPIC returns structured guideline data including recommendation text, classification level, and prescribing implications. A local fallback cache (`backend/app/core/fallback_guidelines.py`) mirrors the most critical CPIC guidelines so the system continues to generate alerts even when the external API is unavailable. Fallback use is logged for audit purposes.

### 6. Interactive Safety Dashboard

Alert results are rendered in the React frontend as a Traffic Light grid. Each medication produces one alert card colored by risk category:

- **RED** - Contraindicated or high-risk combination. An alternative drug is recommended.
- **YELLOW** - Moderate risk. A dose adjustment or increased monitoring is warranted.
- **GREEN** - No clinically significant interaction for this patient's genomic profile.
- **GREY** - Insufficient genomic data. Genetic testing is recommended before prescribing.

Cards are expandable: clicking a card reveals the full CPIC guideline summary, the gene-drug pair involved, the patient's diplotype and phenotype, and the evidence classification level. A "View CPIC Guideline" link opens the corresponding page on the CPIC website (cpicpgx.org), where clinicians can access the full peer-reviewed publication for the drug-gene pair.

---

## System Architecture

```
┌──────────────┐     SMART Launch      ┌────────────────────────────────────────────┐
│  Cerner EHR  │──────────────────────►│              Pharmaco-Navigator            │
│  (FHIR R4)   │◄──────────────────────│  ┌──────────┐   ┌────────────────────┐     │
└──────────────┘   Patient + Meds      │  │  React   │   │      FastAPI       │     │
                                       │  │ Frontend │◄─►│  (BFF / Sessions)  │     │
                                       │  └──────────┘   └────┬───────────────┘     │
                                       │                      │                     │
                                       │       ┌──────────────┼──────────────┐      │
                                       │       ▼              ▼              ▼      │
                                       │ ┌───────────┐  ┌───────────┐  ┌──────────┐ │
                                       │ │Azure PgSQL│  │ CPIC API  │  │ RxNav API│ │
                                       │ │(Genotypes)│  │(Guideline)│  │ (RxCUI)  │ │
                                       │ └───────────┘  └───────────┘  └──────────┘ │
                                       └────────────────────────────────────────────┘
```

**Request flow for alert generation:**

1. Clinician opens Pharmaco-Navigator from within the Cerner EHR (SMART launch).
2. FastAPI completes the OAuth 2.0 authorization code exchange and stores the access token server-side.
3. The frontend sends the patient ID (from the launch context) to `GET /api/v1/patient/{id}/alerts`.
4. The backend fetches active medications from Cerner FHIR R4.
5. Each medication name is normalized to an RxCUI via the RxNav API.
6. Patient star-allele diplotypes are retrieved from Azure PostgreSQL.
7. Diplotypes are translated to metabolizer phenotypes using the Activity Score algorithm.
8. For each drug/gene pair, the CPIC API (or fallback cache) provides a prescribing recommendation.
9. Recommendations are classified as RED / YELLOW / GREEN / GREY and returned to the frontend.
10. The React dashboard renders the Traffic Light alert grid.

---

## Technology Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.129.0 |
| Language | Python | 3.11+ |
| ASGI Server | Uvicorn | 0.41.0 |
| Database ORM | SQLAlchemy (async) | 2.0.46 |
| Database Driver | asyncpg | 0.30.0 |
| HTTP Client | httpx | 0.28.1 |
| Auth / JWT | python-jose | 3.5.0 |
| Data Validation | Pydantic | 2.12.5 |
| Testing | pytest + pytest-asyncio | 8.3.4 |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 18 |
| Build Tool | Vite | Latest |
| Styling | Tailwind CSS | Latest |
| HTTP Client | Axios | Latest |
| Routing | React Router | Latest |
| Unit Tests | Vitest | Latest |
| E2E Tests | Playwright | Latest |

### Database
| Component | Technology |
|-----------|-----------|
| Engine | Azure PostgreSQL 14 |
| Connection Pool | SQLAlchemy 2.0 (async) |
| Encryption at rest | AES-256 |
| Encryption in transit | TLS 1.2+ |

### External Services
| Service | Purpose | Authentication |
|---------|---------|---------------|
| Cerner FHIR R4 | Patient demographics and active medication orders | OAuth 2.0 (SMART on FHIR) |
| CPIC API | Evidence-based pharmacogenomic guidelines | Public API |
| RxNav (NLM) | Drug name to RxCUI normalization | Public API |

---

## Repository Structure

```
pharmaco-navigator/
├── README.md                     # This file
├── SETUP.md                      # Installation and configuration guide
│
├── backend/                      # FastAPI application
│   ├── README.md                 # Backend-specific documentation
│   ├── requirements.txt          # Python dependencies
│   ├── pytest.ini                # Test configuration
│   ├── app/
│   │   ├── main.py               # Application entrypoint, router registration
│   │   ├── api/
│   │   │   ├── deps.py           # Shared FastAPI dependencies
│   │   │   └── v1/
│   │   │       ├── auth.py       # SMART on FHIR OAuth flow
│   │   │       ├── fhir.py       # FHIR resource endpoints
│   │   │       ├── patient.py    # Genomic profile summary
│   │   │       └── alerts.py     # Traffic Light alert generation
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic settings (reads .env)
│   │   │   ├── cpic_tables.py    # CPIC pharmacogenomic reference tables
│   │   │   ├── fallback_guidelines.py  # Local CPIC guideline cache
│   │   │   └── session.py        # BFF session helpers (type-safe accessors)
│   │   ├── db/
│   │   │   └── session.py        # SQLAlchemy async engine and session
│   │   ├── models/
│   │   │   ├── genotype.py       # Genotype ORM model
│   │   │   ├── recommendation.py # Recommendation response model
│   │   │   └── schemas.py        # Pydantic request/response schemas
│   │   └── services/
│   │       ├── fhir_service.py         # Live Cerner FHIR R4 integration
│   │       ├── demo_fhir_service.py    # Synthetic FHIR data (offline testing)
│   │       ├── genomic_service.py      # Genotype retrieval from PostgreSQL
│   │       ├── phenotype_service.py    # Activity Score to metabolizer status
│   │       ├── recommendation_service.py  # Alert orchestration
│   │       ├── cpic_service.py         # CPIC API + fallback guidelines
│   │       └── rxnav_service.py        # RxNav drug normalization
│   ├── db/
│   │   ├── insert_cerner_patients.py   # Seed Cerner sandbox patient genotypes
│   │   ├── insert_demo_patients.sql    # Seed demo patient genotypes
│   │   └── run_sql.py                  # Utility to execute SQL files
│   └── tests/
│       ├── unit/                 # Isolated unit tests (no I/O)
│       ├── api/                  # API endpoint tests (TestClient)
│       ├── integration/          # Integration tests (live DB/APIs)
│       └── e2e/                  # End-to-end tests
│
├── frontend/                     # React SPA
│   ├── README.md                 # Frontend-specific documentation
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx               # Root component and route definitions
│       ├── index.jsx             # React DOM entry point
│       ├── components/
│       │   ├── Dashboard/        # Main dashboard view and header
│       │   ├── Alerts/           # Alert card and grid components
│       │   └── Commons/          # Shared UI (error, loading, icon)
│       ├── hooks/
│       │   └── useLaunchContext.js  # Parses SMART launch URL params
│       ├── services/
│       │   └── api.js            # Axios client for backend API calls
│       └── styles/
│           └── main.css          # Global CSS (Tailwind base + custom overrides)
```

---

## Quick Start

Full setup instructions are in [SETUP.md](SETUP.md). A brief summary:

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Create backend/.env (see SETUP.md)
uvicorn app.main:app --reload

# Frontend 
cd frontend
npm install
npm run dev                     # Starts on http://localhost:3000
```

For demo mode without a Cerner account, use patient IDs `DEMO001` through `DEMO007` directly in the URL: `http://localhost:3000?patient=DEMO001`.

---

## API Endpoints

Full API reference is in [backend/README.md](backend/README.md). Summary:

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/auth/launch` | SMART on FHIR launch entry point |
| GET | `/api/v1/auth/callback` | OAuth 2.0 authorization callback |
| POST | `/api/v1/auth/logout` | Terminate session |
| GET | `/api/v1/auth/session` | Check session status |

### FHIR Resources
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/fhir/patient` | Patient demographics |
| GET | `/api/v1/fhir/medications` | Active medication orders |

### Clinical Insights
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/patient/{id}/summary` | Genomic profile summary |
| GET | `/api/v1/patient/{id}/alerts` | Traffic Light alert set |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check (database + CPIC API) |
| GET | `/docs` | Interactive Swagger UI |

---

## Security

- **OAuth 2.0 PKCE-ready flow** with cryptographic `state` parameter for CSRF protection
- **BFF session pattern**: access tokens never sent to the browser; stored server-side only
- **HttpOnly / Secure / SameSite=Lax cookies** for session tracking
- **No PHI leaves the backend**: RxNav and CPIC are queried with drug names and phenotype labels only - never patient identifiers
- **TLS 1.2+ in transit**, AES-256 at rest for the Azure PostgreSQL database
- **Audit logging** on all authenticated API requests
- **Input validation** via Pydantic 2 models on all request and response types

---

## Error Handling

| Scenario | HTTP Status | System Behavior |
|----------|------------|-----------------|
| Database unreachable | 503 | Returns service unavailable; frontend shows error banner |
| Patient not found in FHIR | 404 | Returns structured error; UI prompts GREY alert with testing recommendation |
| CPIC API unavailable | 200 | Transparently falls back to local guideline cache; fallback use is logged |
| Missing genomic data for gene | 200 | Alert for that gene is classified GREY with recommendation for testing |
| OAuth state mismatch | 400 | Authorization flow aborted; user redirected to error page |

---

## Testing

### Backend

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

### Frontend

```bash
cd frontend

# Unit and integration tests (Vitest)
npm test

# E2E tests (Playwright) - requires backend running on port 8000
npx playwright test

# View Playwright HTML report
npx playwright show-report
```

---

## Documentation

| File | Contents |
|------|----------|
| [SETUP.md](SETUP.md) | Prerequisites, installation, environment variables, database seeding, troubleshooting |
| [backend/README.md](backend/README.md) | API reference, service layer descriptions, data models, test commands |
| [frontend/README.md](frontend/README.md) | Component architecture, routing, hooks, API client, build configuration |

---

## Acknowledgments

- **Cerner** - FHIR R4 sandbox environment for EHR integration testing
- **CPIC** - Clinical Pharmacogenetics Implementation Consortium for evidence-based prescribing guidelines
- **NLM** - National Library of Medicine for the RxNav medication normalization API
- **Microsoft Azure** - Cloud database and infrastructure services

