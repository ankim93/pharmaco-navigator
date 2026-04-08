# Frontend - Pharmaco-Navigator

React single-page application for the Pharmaco-Navigator Clinical Decision Support system. Renders the Traffic Light pharmacogenomic alert dashboard, handles SMART on FHIR launch context, and communicates with the FastAPI backend.

See [SETUP.md](../SETUP.md) at the repository root for full installation instructions.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Component Architecture](#component-architecture)
- [Routing](#routing)
- [Hooks](#hooks)
- [API Client](#api-client)
- [Styling](#styling)
- [Configuration](#configuration)
- [Running the Dev Server](#running-the-dev-server)
- [Testing](#testing)
- [Building for Production](#building-for-production)

---

## Project Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js              # Vite configuration (port 3000, open browser)
├── vitest.config.js            # Vitest configuration for unit/integration tests
├── playwright.config.js        # Playwright configuration for E2E tests
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── index.jsx               # React DOM entry point (mounts <App />)
    ├── App.jsx                 # Root component - defines route structure
    ├── components/
    │   ├── Alerts/
    │   │   ├── AlertCard.jsx   # Single Traffic Light alert card (expandable)
    │   │   └── AlertGrid.jsx   # Grid layout for all alert cards
    │   ├── Commons/
    │   │   ├── ErrorAlert.jsx      # Error state banner
    │   │   ├── LoadingSpinner.jsx  # Loading state indicator
    │   │   └── PharmacoIcon.jsx    # Application icon component
    │   └── Dashboard/
    │       ├── Dashboard.jsx       # Main dashboard view, orchestrates data fetching
    │       └── DashboardHeader.jsx # Header with patient name and session info
    ├── hooks/
    │   ├── index.js                # Hook re-exports
    │   └── useLaunchContext.js     # Parses SMART on FHIR launch parameters from URL
    ├── services/
    │   └── api.js                  # Axios API client for backend communication
    └── styles/
        └── main.css                # Global CSS (Tailwind base + custom overrides)
```

---

## Component Architecture

### `App.jsx`

Root component. Reads the `?patient=` query parameter from the URL and passes it down as the active patient context. Renders the `Dashboard` or an error view if no patient context is available.

### `Dashboard/Dashboard.jsx`

The primary view component. On mount, calls `fetchPatientAlerts(patientId)` from the API service and manages three UI states: loading, error, and success. On success, passes the structured alert set to `AlertGrid`. Re-fetches on patient context change.

### `Dashboard/DashboardHeader.jsx`

Displays the patient identifier, session state, and application title. Provides the logout action button.

### `Alerts/AlertGrid.jsx`

Receives the full alert payload and renders four labeled sections - RED, YELLOW, GREEN, GREY - each containing the relevant `AlertCard` list. Shows section-level empty state messages when a category has no alerts.

### `Alerts/AlertCard.jsx`

Renders a single alert. The card is color-coded by category (red, yellow, green, grey border and background tints). It is collapsed by default, showing only the drug name and risk category. Clicking the card expands it to reveal:

- Gene symbol and diplotype
- Translated metabolizer phenotype
- Full CPIC recommendation text
- Evidence classification level

### `Commons/ErrorAlert.jsx`

Renders a structured error banner for backend API failures. Displays the error message and a retry button. Used by `Dashboard` in the error state.

### `Commons/LoadingSpinner.jsx`

Centered spinning indicator used during API requests.

### `Commons/PharmacoIcon.jsx`

SVG application icon component, used in the header.

---

## Routing

The application uses React Router. The primary route is `/` which renders `App.jsx`. The `?patient=` query parameter carries the patient identifier from the SMART on FHIR launch URL. There are no separate page routes - the entire application is a single-page dashboard.

**Demo URL format:**
```
http://localhost:3000/?patient=DEMO001
```

**SMART launch URL format (set by the EHR):**
```
http://localhost:3000/?iss=https://fhir-ehr-code.cerner.com/r4/<tenant>&launch=<token>
```

---

## Hooks

### `useLaunchContext.js`

Reads and parses query parameters from the current URL using `window.location.search`. Returns an object containing `patientId`, `iss` (FHIR server URL), and `launch` token when present. Used by `App.jsx` to determine whether the app was opened via SMART launch or direct URL.

---

## API Client

`src/services/api.js` creates a configured Axios instance and exports typed request functions.

**Base URL**: Reads from `VITE_API_BASE_URL` environment variable, defaulting to `http://localhost:8000/api/v1`.

**Configuration**:
- `withCredentials: true` - includes the session cookie on every request (required for BFF authentication)
- `timeout: 15000` - 15-second request timeout
- Response interceptor normalizes all HTTP error codes into JavaScript `Error` objects with descriptive messages

**Exported functions**:

| Function | Endpoint | Returns |
|----------|----------|---------|
| `fetchPatientAlerts(patientId)` | `GET /patient/{id}/alerts` | Alert payload with RED/YELLOW/GREEN/GREY lists |
| `fetchPatientSummary(patientId)` | `GET /patient/{id}/summary` | Genomic profile summary |
| `fetchSession()` | `GET /auth/session` | Session status and patient context |
| `logout()` | `POST /auth/logout` | Confirms session cleared |

---

## Styling

The application uses **Tailwind CSS** with utility classes throughout all components. Global base styles and Tailwind directives are in `src/styles/main.css`.

Alert card colors follow the Traffic Light convention:
- RED: `border-red-500`, `bg-red-50`
- YELLOW: `border-yellow-400`, `bg-yellow-50`
- GREEN: `border-green-500`, `bg-green-50`
- GREY: `border-gray-400`, `bg-gray-50`

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API base URL. Set in `frontend/.env` for non-default backends. |

Create `frontend/.env` if you need to override defaults:

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

The dev server runs on port **3000** (configured in `vite.config.js`).

---

## Running the Dev Server

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:3000`. The server uses Vite HMR (Hot Module Replacement) for instant updates on file changes.

---

## Testing

### Unit and integration tests (Vitest)

```bash
cd frontend
npm test
```

Vitest runs all `*.test.jsx` and `*.test.js` files under `frontend/tests/`. Tests mock API responses via `vi.mock` and render components with React Testing Library.

### End-to-end tests (Playwright)

```bash
# Requires backend running on http://localhost:8000
cd frontend
npx playwright test

# With UI mode
npx playwright test --ui

# Single test file
npx playwright test tests/e2e/dashboard.spec.js
```

Playwright reports are saved to `frontend/playwright-report/`. Screenshots are saved to `frontend/playwright-screenshots/`.

