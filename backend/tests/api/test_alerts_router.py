"""
API router tests for /api/v1/alerts endpoints.
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient

PATIENT_ID = "12724067"
OTHER_PATIENT = "99999999"
ALERTS_URL = f"/api/v1/alerts/{PATIENT_ID}"


# GET /alerts/{patient_id}
@pytest.mark.unit
async def test_get_alerts_returns_401_when_not_authenticated(
    async_client: AsyncClient,
) -> None:
    """
    No active session -> require_authentication raises 401 Unauthorized.
    """
    response = await async_client.get(ALERTS_URL)
    assert response.status_code == 401


@pytest.mark.unit
async def test_get_alerts_returns_403_when_patient_id_mismatch(
    async_client: AsyncClient,
) -> None:
    """
    Session belongs to a different patient than the URL parameter
    -> 403 Security Context Error.
    """
    with (
        patch("app.api.v1.alerts.require_authentication"),
        patch("app.api.v1.alerts.get_patient_id", return_value=OTHER_PATIENT),
    ):
        response = await async_client.get(ALERTS_URL)

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "mismatch" in detail.lower() or "Patient ID" in detail


@pytest.mark.unit
async def test_get_alerts_returns_200_with_dashboard_structure(
    async_client: AsyncClient,
) -> None:
    """
    Authenticated session matches URL patient → 200 with AlertDashboard fields.
    """
    with (
        patch("app.api.v1.alerts.require_authentication"),
        patch("app.api.v1.alerts.get_patient_id", return_value=PATIENT_ID),
    ):
        response = await async_client.get(ALERTS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["patientId"] == PATIENT_ID
    for field in (
        "highRisk",
        "moderateRisk",
        "noRisk",
        "dataMissing",
        "totalMedications",
        "genomicDataComplete",
    ):
        assert field in body
