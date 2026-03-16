"""
API router tests for /api/v1/patient endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from app.models.recommendation import ClinicalAlertResponse, GenomicProfileSummary
from app.services.genomic_service import GenomicConnectionError, GenomicDataNotFoundError


PATIENT_ID = "12724067"
SUMMARY_URL = f"/api/v1/patient/{PATIENT_ID}/summary"
ALERTS_URL = f"/api/v1/patient/{PATIENT_ID}/alerts"


def _make_summary() -> GenomicProfileSummary:
    return GenomicProfileSummary(
        patient_id=PATIENT_ID,
        genes_analyzed=["CYP2D6", "CYP2C19"],
        genes_missing=["SLCO1B1", "ABCB1"],
        phenotypes={
            "CYP2D6": "Normal Metabolizer",
            "CYP2C19": "Normal Metabolizer",
            "SLCO1B1": "Data Missing/Unknown",
            "ABCB1": "Data Missing/Unknown",
        },
    )


def _make_alerts() -> ClinicalAlertResponse:
    return ClinicalAlertResponse(
        patient_id=PATIENT_ID,
        red_alerts=[],
        yellow_alerts=[],
        green_alerts=[],
        grey_alerts=[],
        active_medications=[],
        total_medications=0,
    )


# GET /patient/{id}/summary
@pytest.mark.unit
async def test_summary_returns_200_with_valid_shape(async_client: AsyncClient) -> None:
    """
    Happy-path: mocked service returns data -> 200 with all required fields.
    """
    svc = MagicMock()
    svc.get_genomic_summary = AsyncMock(return_value=_make_summary())

    with patch("app.api.v1.patient.create_recommendation_service", return_value=svc):
        response = await async_client.get(SUMMARY_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["patient_id"] == PATIENT_ID
    assert "genes_analyzed" in body
    assert "genes_missing" in body
    assert "phenotypes" in body


@pytest.mark.unit
async def test_summary_returns_404_when_patient_not_found(async_client: AsyncClient) -> None:
    """
    Patient absent from genomic DB -> 404 with informative detail.
    """
    svc = MagicMock()
    svc.get_genomic_summary = AsyncMock(
        side_effect=GenomicDataNotFoundError("No data for patient")
    )

    with patch("app.api.v1.patient.create_recommendation_service", return_value=svc):
        response = await async_client.get(SUMMARY_URL)

    assert response.status_code == 404
    assert "No genomic data" in response.json()["detail"]


@pytest.mark.unit
async def test_summary_returns_503_when_db_unavailable(async_client: AsyncClient) -> None:
    """
    Azure PostgreSQL unreachable -> 503 Service Unavailable.
    """
    svc = MagicMock()
    svc.get_genomic_summary = AsyncMock(
        side_effect=GenomicConnectionError("Connection refused")
    )

    with patch("app.api.v1.patient.create_recommendation_service", return_value=svc):
        response = await async_client.get(SUMMARY_URL)

    assert response.status_code == 503


# GET /patient/{id}/alerts
@pytest.mark.unit
async def test_alerts_returns_200_with_traffic_light_structure(async_client: AsyncClient) -> None:
    """
    Happy-path: mocked service -> 200 with all four alert colour buckets.
    """
    svc = MagicMock()
    svc.generate_clinical_alerts = AsyncMock(return_value=_make_alerts())

    with patch("app.api.v1.patient.get_recommendation_service", return_value=svc):
        response = await async_client.get(ALERTS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["patient_id"] == PATIENT_ID
    for field in ("red_alerts", "yellow_alerts", "green_alerts", "grey_alerts", "total_medications"):
        assert field in body


@pytest.mark.unit
async def test_alerts_returns_404_when_patient_not_found(async_client: AsyncClient) -> None:
    """
    Patient absent from genomic DB -> 404.
    """
    svc = MagicMock()
    svc.generate_clinical_alerts = AsyncMock(
        side_effect=GenomicDataNotFoundError("Patient not found")
    )

    with patch("app.api.v1.patient.get_recommendation_service", return_value=svc):
        response = await async_client.get(ALERTS_URL)

    assert response.status_code == 404


@pytest.mark.unit
async def test_alerts_returns_503_when_db_unavailable(async_client: AsyncClient) -> None:
    """
    Azure PostgreSQL unreachable -> 503 Service Unavailable.
    """
    svc = MagicMock()
    svc.generate_clinical_alerts = AsyncMock(
        side_effect=GenomicConnectionError("DB unreachable")
    )

    with patch("app.api.v1.patient.get_recommendation_service", return_value=svc):
        response = await async_client.get(ALERTS_URL)

    assert response.status_code == 503
