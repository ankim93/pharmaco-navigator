"""
API router tests for /api/v1/fhir endpoints.
"""

import pytest
import respx
import httpx
from unittest.mock import patch
from httpx import AsyncClient


# Fixed FHIR base URL injected via the patched get_fhir_server_url
FHIR_BASE = "https://fhir.test.local"
PATIENT_ID = "12724067"

_FHIR_PATIENT = {
    "resourceType": "Patient",
    "id": PATIENT_ID,
    "name": [{"family": "Smith", "given": ["John"]}],
    "birthDate": "1980-01-01",
    "gender": "male",
}

_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "type": "searchset",
    "total": 1,
    "entry": [
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-001",
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {"text": "Codeine"},
                "subject": {"reference": f"Patient/{PATIENT_ID}"},
                "authoredOn": "2025-01-15",
            }
        }
    ],
}


def _auth_patches():
    """
    Return three patch context managers that satisfy all session checks inside
    fhir.py without needing a real signed session cookie.
    """
    return (
        patch("app.api.v1.fhir.require_authentication"),
        patch(
            "app.api.v1.fhir.get_authorization_header",
            return_value={"Authorization": "Bearer test-access-token"},
        ),
        patch(
            "app.api.v1.fhir.get_fhir_server_url",
            return_value=FHIR_BASE,
        ),
    )


# GET /fhir/patient/{id}
@pytest.mark.unit
async def test_get_patient_returns_401_when_not_authenticated(
    async_client: AsyncClient,
) -> None:
    """
    No active session -> require_authentication raises 401 Unauthorized.
    """
    response = await async_client.get(f"/api/v1/fhir/patient/{PATIENT_ID}")
    assert response.status_code == 401


@pytest.mark.unit
async def test_get_patient_returns_200_with_fhir_patient_resource(
    async_client: AsyncClient,
) -> None:
    """
    Authenticated; FHIR server returns a valid Patient resource -> 200.
    """
    p1, p2, p3 = _auth_patches()
    with p1, p2, p3, respx.mock:
        respx.get(f"{FHIR_BASE}/Patient/{PATIENT_ID}").mock(
            return_value=httpx.Response(200, json=_FHIR_PATIENT)
        )
        response = await async_client.get(f"/api/v1/fhir/patient/{PATIENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["resourceType"] == "Patient"
    assert body["id"] == PATIENT_ID


@pytest.mark.unit
async def test_get_patient_returns_404_when_fhir_says_not_found(
    async_client: AsyncClient,
) -> None:
    """
    FHIR server returns 404 -> router maps to 404 Not Found.
    """
    p1, p2, p3 = _auth_patches()
    with p1, p2, p3, respx.mock:
        respx.get(f"{FHIR_BASE}/Patient/{PATIENT_ID}").mock(
            return_value=httpx.Response(404, json={"resourceType": "OperationOutcome"})
        )
        response = await async_client.get(f"/api/v1/fhir/patient/{PATIENT_ID}")

    assert response.status_code == 404


@pytest.mark.unit
async def test_get_patient_returns_502_on_fhir_server_error(
    async_client: AsyncClient,
) -> None:
    """
    FHIR server returns 5xx -> router maps to 502 Bad Gateway.
    """
    p1, p2, p3 = _auth_patches()
    with p1, p2, p3, respx.mock:
        respx.get(f"{FHIR_BASE}/Patient/{PATIENT_ID}").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        response = await async_client.get(f"/api/v1/fhir/patient/{PATIENT_ID}")

    assert response.status_code == 502


# GET /fhir/medications/{id}
@pytest.mark.unit
async def test_get_medications_returns_401_when_not_authenticated(
    async_client: AsyncClient,
) -> None:
    """
    No active session -> 401 Unauthorized.
    """
    response = await async_client.get(f"/api/v1/fhir/medications/{PATIENT_ID}")
    assert response.status_code == 401


@pytest.mark.unit
async def test_get_medications_returns_200_with_fhir_bundle(
    async_client: AsyncClient,
) -> None:
    """
    Authenticated; FHIR returns a valid MedicationRequest Bundle -> 200.
    """
    med_url = (
        f"{FHIR_BASE}/MedicationRequest"
        f"?patient={PATIENT_ID}&status=active&_count=100"
    )
    p1, p2, p3 = _auth_patches()
    with p1, p2, p3, respx.mock:
        respx.get(med_url).mock(
            return_value=httpx.Response(200, json=_FHIR_BUNDLE)
        )
        response = await async_client.get(f"/api/v1/fhir/medications/{PATIENT_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["resourceType"] == "Bundle"
    assert body["total"] == 1
