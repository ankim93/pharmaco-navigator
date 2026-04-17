# Setup Guide - Pharmaco-Navigator

This guide covers everything required to get Pharmaco-Navigator running locally, from prerequisites through to a working application with demo patients.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Clone the Repository](#clone-the-repository)
- [Backend Setup](#backend-setup)
  - [Create a Python Virtual Environment](#create-a-python-virtual-environment)
  - [Install Python Dependencies](#install-python-dependencies)
  - [Configure Environment Variables](#configure-environment-variables)
  - [Initialize the Database](#initialize-the-database)
  - [Seed Patient Data](#seed-patient-data)
- [Frontend Setup](#frontend-setup)
  - [Install Node Dependencies](#install-node-dependencies)
- [Running the Application](#running-the-application)
  - [Start the Backend](#start-the-backend)
  - [Start the Frontend](#start-the-frontend)
- [Usage Modes](#usage-modes)
  - [Demo Mode](#demo-mode)
  - [Cerner SMART on FHIR Mode](#cerner-smart-on-fhir-mode)
- [Running Tests](#running-tests)
  - [Backend Tests](#backend-tests)
  - [Frontend Tests](#frontend-tests)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|:--------------:|-------|
| Python | 3.11 | Required for the backend |
| Node.js | 18 | Required for the frontend |
| npm | 9 | Included with Node.js |
| PostgreSQL | 14 | Azure Database for PostgreSQL (Flexible Server) recommended |
| Git | Any | For cloning the repository |

For the Cerner SMART on FHIR mode you also need:

- A Cerner developer account with an approved SMART on FHIR application
- A registered `client_id` and `client_secret` from the Cerner developer portal
- Access to a Cerner FHIR R4 tenant (the sandbox tenant is `ec2458f2-1e24-41c8-b71b-0e701af7583d`)

For demo mode without a Cerner account, none of the Cerner credentials are actively used during requests (though the settings validator requires them to be non-empty - use placeholder values).

---

## Backend Setup

### Create a Python Virtual Environment

```bash
cd backend
python -m venv .venv
```

Activate the environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

Your terminal prompt should show `(.venv)` when the environment is active. All subsequent Python and pip commands in this section assume the environment is active.

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs all runtime and test dependencies including FastAPI, SQLAlchemy, asyncpg, httpx, pytest, respx, and others listed in `requirements.txt`.

### Configure Environment Variables

Copy the provided template and fill in your values:

```bash
cp .env.example .env
```

Then open `backend/.env` and replace the placeholder values. Generate a secure `SECRET_KEY` with:

```bash
openssl rand -hex 32
```

### Initialize the Database

Connect to your PostgreSQL instance and create the database and schema:

```sql
-- Run as a superuser or database owner
CREATE DATABASE pharmaco_genomics;

\c pharmaco_genomics

CREATE TABLE genotypes (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(255) NOT NULL,
    gene_symbol VARCHAR(50) NOT NULL,
    allele_1 VARCHAR(50) NOT NULL,
    allele_2 VARCHAR(50) NOT NULL,
    diplotype VARCHAR(100),
    activity_score FLOAT,
    phenotype VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_genotypes_patient_id ON genotypes(patient_id);
CREATE INDEX idx_genotypes_gene_symbol ON genotypes(gene_symbol);
```

For Azure Database for PostgreSQL (Flexible Server), use the Azure portal Query Editor or `psql` with the server connection string from the Azure portal.

### Seed Patient Data

#### Demo patients

Loads synthetic genotype data for patients `DEMO001` through `DEMO006`. Note that `DEMO007` is intentionally absent — it tests the missing-data GREY alert path.

```bash
cd backend
python db/run_sql.py db/insert_demo_patients.sql
```

#### Cerner sandbox patients

Loads genotype records for 9 real Cerner FHIR sandbox patient identifiers.

```bash
python db/insert_cerner_patients.py
```

This script reads `DATABASE_URL` from your `.env` file.

---

## Frontend Setup

### Install Node Dependencies

```bash
cd frontend
npm install
```

#### Optional: configure API base URL

The frontend defaults to `http://localhost:8000/api/v1`. If your backend is on a different host or port, create `frontend/.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## Running the Application

Open two terminal windows. Both require their respective environments to be active.

### Start the Backend

```bash
cd backend
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`.  
Swagger UI (interactive API docs) is at `http://localhost:8000/docs`.

Verify the server is healthy:
```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "database": { "status": "connected" },
    "cpic_api": { "status": "operational" }
  }
}
```

### Start the Frontend

```bash
cd frontend
npm run dev
```

The application opens at `http://localhost:3000`.

---

## Usage Modes

### Demo Mode

Demo mode uses synthetic patient data stored in the database and does not require a Cerner account or live EHR connection.

Access any demo patient by appending `?patient=<ID>` to the frontend URL:

| Patient ID | Profile Description |
|------------|-------------------|
| `DEMO001` | CYP2D6 Poor Metabolizer - expects RED alerts for codeine-class drugs |
| `DEMO002` | CYP2C19 Ultrarapid Metabolizer - expects alerts for clopidogrel, PPIs |
| `DEMO003` | CYP2C9 Intermediate Metabolizer - expects alerts for warfarin |
| `DEMO004` | SLCO1B1 Decreased Function - expects alerts for statins |
| `DEMO005` | Normal metabolizers across all genes - expects GREEN alerts |
| `DEMO006` | Multiple gene variants - mixed RED/YELLOW/GREEN alerts |
| `DEMO007` | No genomic data on file - expects all GREY alerts |

Example URL:
```
http://localhost:3000/?patient=DEMO001
```

The backend automatically routes IDs matching `DEMO001`–`DEMO007` to the synthetic FHIR service instead of calling Cerner.

### Cerner SMART on FHIR Mode

For live EHR integration using the Cerner sandbox:

1. Ensure all `CERNER_*` variables are set correctly in `backend/.env`.
2. Ensure the `CERNER_REDIRECT_URI` registered in the Cerner developer portal exactly matches the value in `.env`.
3. Trigger a SMART launch from the Cerner Code Console by clicking **Test Sandbox**, or open the launch URL directly:

```
http://localhost:8000/api/v1/auth/launch?iss=https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d&launch=<launch_token>
```

The backend will:
1. Redirect to the Cerner authorization server where you input the provided username and password.
2. After clinician approval, receive the callback at `/api/v1/auth/callback`.
3. Exchange the authorization code for tokens.
4. Redirect the browser to the React frontend with the patient context in the URL.

---

## Running Tests

### Backend Tests

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

### Frontend Tests

```bash
cd frontend

# Unit and integration tests (Vitest)
npm test

# E2E tests (Playwright) - requires backend running on port 8000
npx playwright test

# View Playwright HTML report
npx playwright show-report
```