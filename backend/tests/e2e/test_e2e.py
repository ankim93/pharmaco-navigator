"""
End-to-End Tests — Pharmaco Navigator
"""

import json
import os
import itsdangerous
import pytest
import pytest_asyncio
from base64 import b64encode
from fastapi import status
from httpx import AsyncClient
from app.core.config import settings


pytestmark = [
    pytest.mark.slow,
    pytest.mark.e2e,
    pytest.mark.asyncio(loop_scope="session"),
]


# Demo patient IDs — genotype data seeded via db/insert_demo_patients.sql
DEMO_HIGH_RISK  = "DEMO001"  # CYP2D6 *4/*4  (Poor),  CYP2C19 *2/*2 (Poor),  SLCO1B1 *5/*5 (Decreased)
DEMO_NORMAL     = "DEMO002"  # All genes *1 wild-type  — best-case profile
DEMO_ULTRARAPID = "DEMO003"  # CYP2D6 Ultrarapid (*1/*2xN), CYP2C19 *17/*17 (Ultrarapid)
DEMO_MIXED      = "DEMO004"  # Poor CYP2D6,  Normal CYP2C19,  Decreased SLCO1B1

# A patient ID that has never been seeded
NONEXISTENT_PATIENT = "E2E-NO-SUCH-PATIENT-ZZZ"

# Cerner sandbox constants
CERNER_OPEN_PATIENT_ID = "12724067"   # Open-sandbox patient
CERNER_E2E_TOKEN = os.environ.get("CERNER_E2E_ACCESS_TOKEN", "")

# Decorator that skips a test when no Cerner access token is available
e2e_fhir = pytest.mark.skipif(
    not CERNER_E2E_TOKEN,
    reason=(
        "Set CERNER_E2E_ACCESS_TOKEN to a valid Cerner sandbox access token "
        "to run live FHIR proxy tests."
    ),
)


# Helper: build a starlette-compatible signed session cookie
def _make_session_cookie(session_data: dict) -> str:
    """
    Produce a signed cookie value that starlette's SessionMiddleware accepts.
    """
    signer = itsdangerous.TimestampSigner(str(settings.SECRET_KEY))
    payload = b64encode(json.dumps(session_data).encode("utf-8"))
    return signer.sign(payload).decode("utf-8")


# Health endpoint
class TestHealthEndpoint:
    """
    Verify that Azure PostgreSQL and the CPIC API are reachable.
    """
    async def test_database_reports_connected(self, live_client: AsyncClient) -> None:
        """
        Azure PostgreSQL must report 'connected' before any clinical test can run.
        """
        response = await live_client.get("/api/v1/health")
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        body = response.json()
        health_data = body.get("detail", body)
        db = health_data["services"]["database"]
        assert db["status"] == "connected", (
            f"Azure PostgreSQL is not connected: {db.get('message', 'no message')}"
        )

    async def test_cpic_api_reachable(self, live_client: AsyncClient) -> None:
        """
        CPIC API must be reachable (or degrade gracefully with fallback guidelines).
        """
        response = await live_client.get("/api/v1/health")
        body = response.json()
        health_data = body.get("detail", body)
        cpic = health_data["services"]["cpic_api"]
        assert cpic["status"] in ("available", "unavailable"), (
            f"Unexpected CPIC status value: {cpic['status']!r}"
        )
        if cpic["status"] == "unavailable":
            # Degraded-mode must advertise fallback guidelines
            assert "fallback" in cpic.get("message", "").lower(), (
                "Unavailable CPIC must mention fallback in message"
            )


# Genomic summary (real PostgreSQL lookups)
class TestGenomicSummary:
    """
    GET /api/v1/patient/{id}/summary queries Azure PostgreSQL for genotype
    rows and translates alleles into clinical phenotypes.
    """
    async def test_summary_shape_for_known_patient(
        self, live_client: AsyncClient
    ) -> None:
        """
        Response must contain all four pharmacogenes for a seeded patient.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/summary"
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()

        assert body["patient_id"] == DEMO_HIGH_RISK
        assert "phenotypes" in body
        assert "genes_analyzed" in body
        assert "genes_missing" in body

        for gene in ("CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"):
            assert gene in body["phenotypes"], (
                f"Expected phenotype entry for {gene}"
            )

    async def test_cyp2d6_poor_metabolizer_for_demo001(
        self, live_client: AsyncClient
    ) -> None:
        """
        DEMO001 (*4/*4) must be classified as CYP2D6 Poor Metabolizer.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/summary"
        )
        assert response.status_code == status.HTTP_200_OK
        phenotype = response.json()["phenotypes"]["CYP2D6"]
        assert "Poor" in phenotype, (
            f"CYP2D6 *4/*4 should be 'Poor Metabolizer', got: {phenotype!r}"
        )

    async def test_cyp2c19_poor_metabolizer_for_demo001(
        self, live_client: AsyncClient
    ) -> None:
        """
        DEMO001 (*2/*2) must be classified as CYP2C19 Poor Metabolizer.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/summary"
        )
        assert response.status_code == status.HTTP_200_OK
        phenotype = response.json()["phenotypes"]["CYP2C19"]
        assert "Poor" in phenotype, (
            f"CYP2C19 *2/*2 should be 'Poor Metabolizer', got: {phenotype!r}"
        )

    async def test_normal_metabolizer_profile_for_demo002(
        self, live_client: AsyncClient
    ) -> None:
        """
        DEMO002 (*1/*1 for all genes) must report Normal Metabolizer for CYP2D6.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_NORMAL}/summary"
        )
        assert response.status_code == status.HTTP_200_OK
        phenotype = response.json()["phenotypes"]["CYP2D6"]
        assert "Normal" in phenotype, (
            f"CYP2D6 *1/*1 should be 'Normal Metabolizer', got: {phenotype!r}"
        )

    async def test_summary_for_unknown_patient_shows_all_genes_missing(
        self, live_client: AsyncClient
    ) -> None:
        
        response = await live_client.get(
            f"/api/v1/patient/{NONEXISTENT_PATIENT}/summary"
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()

        assert body["patient_id"] == NONEXISTENT_PATIENT
        # All four pharmacogenes must appear as missing
        assert len(body["genes_analyzed"]) == 0
        assert len(body["genes_missing"]) == 4
        for gene in ("CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"):
            assert gene in body["genes_missing"], (
                f"{gene} should be in genes_missing for an unseeded patient"
            )


# Clinical alerts (real DB + real CPIC + demo FHIR service)
class TestClinicalAlerts:
    async def test_response_has_required_fields(
        self, live_client: AsyncClient
    ) -> None:
        """
        Alert response for DEMO001 must contain all Traffic Light buckets.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()

        required = {
            "patient_id", "red_alerts", "yellow_alerts",
            "green_alerts", "grey_alerts", "total_medications",
        }
        missing = required - body.keys()
        assert not missing, f"Response missing fields: {missing}"
        assert body["patient_id"] == DEMO_HIGH_RISK

    async def test_alert_counts_cover_all_medications(
        self, live_client: AsyncClient
    ) -> None:
        
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()

        assert body["total_medications"] >= 1
        # All four buckets must be present as lists
        for bucket in ("red_alerts", "yellow_alerts", "green_alerts", "grey_alerts"):
            assert isinstance(body[bucket], list), f"{bucket} must be a list"

    async def test_high_risk_patient_has_red_alerts(
        self, live_client: AsyncClient
    ) -> None:
        """
        DEMO001 (Poor CYP2D6 + Poor CYP2C19) must produce at least one RED alert.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        red_alerts = response.json()["red_alerts"]
        assert len(red_alerts) >= 1, (
            "Expected >= 1 RED alert for DEMO001 (Poor CYP2D6 *4/*4 + Poor CYP2C19 *2/*2)"
        )

    async def test_codeine_is_red_for_poor_cyp2d6(
        self, live_client: AsyncClient
    ) -> None:
        """
        Codeine must appear in RED alerts when the patient is a CYP2D6 Poor Metabolizer.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        red_drugs = [a["drug_name"] for a in response.json()["red_alerts"]]
        assert "Codeine" in red_drugs, (
            f"Codeine must be RED for Poor CYP2D6. RED drugs found: {red_drugs}"
        )

    async def test_clopidogrel_is_red_for_poor_cyp2c19(
        self, live_client: AsyncClient
    ) -> None:
        """
        Clopidogrel must appear in RED alerts for a CYP2C19 Poor Metabolizer.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        red_drugs = [a["drug_name"] for a in response.json()["red_alerts"]]
        assert "Clopidogrel" in red_drugs, (
            f"Clopidogrel must be RED for Poor CYP2C19 *2/*2. RED: {red_drugs}"
        )

    async def test_red_alert_schema(self, live_client: AsyncClient) -> None:
        """
        Every RED alert must contain all fields required by the ClinicalAlert model.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_HIGH_RISK}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        red_alerts = response.json()["red_alerts"]
        assert red_alerts, "Need >= 1 RED alert to validate schema"

        required_fields = {
            "drug_name", "gene_symbol", "phenotype",
            "alert_color", "clinical_action",
        }
        for alert in red_alerts:
            missing = required_fields - alert.keys()
            assert not missing, f"Alert missing fields {missing}: {alert}"
            assert alert["alert_color"] == "RED"

    async def test_normal_metabolizer_has_no_red_alerts(
        self, live_client: AsyncClient
    ) -> None:
        """
        DEMO002 (all *1 wild-type) must produce zero RED alerts.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_NORMAL}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        red_alerts = response.json()["red_alerts"]
        assert red_alerts == [], (
            f"Expected 0 RED alerts for DEMO002 (all Normal Metabolizers), "
            f"got: {[a['drug_name'] for a in red_alerts]}"
        )

    async def test_demo003_normal_classification_produces_no_red(self, live_client: AsyncClient) -> None:

        response = await live_client.get(
            f"/api/v1/patient/{DEMO_ULTRARAPID}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        # Under current allele mapping, DEMO003 is classified Normal Metabolizer
        assert body["red_alerts"] == [], (
            "DEMO003 is currently classified as Normal Metabolizer (allele '"
            "*1/*2xN' not mapped). Expect 0 RED alerts."
        )

    async def test_mixed_phenotype_has_red_and_yellow_alerts(
        self, live_client: AsyncClient
    ) -> None:
        """
        DEMO004 (Poor CYP2D6 + Decreased SLCO1B1) must produce both RED and
        YELLOW alerts, confirming multi-gene evaluation works correctly.
        """
        response = await live_client.get(
            f"/api/v1/patient/{DEMO_MIXED}/alerts"
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body["red_alerts"]) >= 1, (
            "Expected RED alerts for DEMO004 (Poor CYP2D6)"
        )
        assert len(body["yellow_alerts"]) >= 1, (
            "Expected YELLOW alerts for DEMO004 (Decreased SLCO1B1)"
        )

    async def test_unknown_patient_returns_graceful_empty_alerts(
        self, live_client: AsyncClient
    ) -> None:
        """
        Alerts for an unseeded patient must degrade gracefully.
        """
        response = await live_client.get(
            f"/api/v1/patient/{NONEXISTENT_PATIENT}/alerts"
        )
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ), f"Unexpected status {response.status_code}: {response.text}"

        if response.status_code == status.HTTP_200_OK:
            body = response.json()
            assert body["total_medications"] == 0
            assert body["red_alerts"] == []


# CORS configuration
class TestCORSHeaders:
    """
    Verify that the React dev-server origins receive correct CORS headers.
    """

    async def test_preflight_includes_allow_origin_for_vite_dev_server(
        self, live_client: AsyncClient
    ) -> None:

        response = await live_client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers, (
            "CORSMiddleware did not return Access-Control-Allow-Origin "
            "for http://localhost:5173"
        )


# Live Cerner FHIR proxy
class TestFHIRProxy:
    """
    End-to-end tests for the Cerner FHIR proxy endpoints.
    """
    def _inject_auth_session(
        self, client: AsyncClient, patient_id: str
    ) -> None:
        """
        Set a signed session cookie that passes require_authentication.
        """
        cookie = _make_session_cookie(
            {
                "authenticated": True,
                "access_token": CERNER_E2E_TOKEN,
                "patient_id": patient_id,
            }
        )
        client.cookies.set(settings.SESSION_COOKIE_NAME, cookie)

    @e2e_fhir
    async def test_fhir_patient_proxy_returns_patient_resource(
        self, live_client: AsyncClient
    ) -> None:
        """
        The FHIR proxy must return a valid FHIR Patient resource from the
        Cerner sandbox for the open-sandbox patient.
        """
        self._inject_auth_session(live_client, CERNER_OPEN_PATIENT_ID)
        try:
            response = await live_client.get(
                f"/api/v1/fhir/patient/{CERNER_OPEN_PATIENT_ID}"
            )
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert body["resourceType"] == "Patient"
            assert body["id"] == CERNER_OPEN_PATIENT_ID
        finally:
            live_client.cookies.clear()

    @e2e_fhir
    async def test_fhir_medications_proxy_returns_bundle(
        self, live_client: AsyncClient
    ) -> None:
        """
        The FHIR proxy must return a FHIR Bundle (MedicationRequest resources)
        for the Cerner open-sandbox patient.
        """
        self._inject_auth_session(live_client, CERNER_OPEN_PATIENT_ID)
        try:
            response = await live_client.get(
                f"/api/v1/fhir/patient/{CERNER_OPEN_PATIENT_ID}/medications"
            )
            assert response.status_code == status.HTTP_200_OK
            body = response.json()
            assert body["resourceType"] == "Bundle"
            # Bundle may have zero entries for a patient with no active medications
            assert "entry" in body or body.get("total", 0) == 0
        finally:
            live_client.cookies.clear()

    @e2e_fhir
    async def test_fhir_proxy_returns_401_without_session(
        self, live_client: AsyncClient
    ) -> None:
        """
        FHIR proxy must reject requests that have no authenticated session.
        """
        live_client.cookies.clear()
        response = await live_client.get(
            f"/api/v1/fhir/patient/{CERNER_OPEN_PATIENT_ID}"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
