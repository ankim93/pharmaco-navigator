"""
Unit tests for app/services/fhir_service.py — HTTP interactions mocked via respx.
"""

import pytest
import httpx
import respx

FHIR_BASE  = "https://fhir.cerner.com/r4/ec2458f2"
FHIR_TOKEN = "test-access-token-xyz"

_FHIR_PATIENT_PAYLOAD = {
    "resourceType": "Patient",
    "id": "12724067",
    "name": [{"use": "official", "text": "John Doe", "family": "Doe", "given": ["John"]}],
    "gender": "male",
    "birthDate": "1980-01-01",
}

_FHIR_BUNDLE_PAYLOAD = {
    "resourceType": "Bundle",
    "type": "searchset",
    "total": 1,
    "entry": [
        {
            "fullUrl": f"{FHIR_BASE}/MedicationRequest/123",
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "123",
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {"text": "Codeine"},
                "subject": {"reference": "Patient/12724067"},
            },
        }
    ],
}


@pytest.mark.unit
class TestFHIRService:

    def _service(self):
        from app.services.fhir_service import FHIRService
        return FHIRService(access_token=FHIR_TOKEN, fhir_base_url=FHIR_BASE)

    # get_patient_demographics
    @pytest.mark.asyncio
    async def test_get_patient_demographics_success(self):
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/Patient/12724067").mock(
                return_value=httpx.Response(200, json=_FHIR_PATIENT_PAYLOAD)
            )
            patient = await svc.get_patient_demographics("12724067")
        assert patient.id == "12724067"

    @pytest.mark.asyncio
    async def test_get_patient_demographics_401_raises_auth_error(self):
        from app.services.fhir_service import FHIRAuthenticationError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/Patient/X").mock(
                return_value=httpx.Response(401, json={"error": "Unauthorized"})
            )
            with pytest.raises(FHIRAuthenticationError):
                await svc.get_patient_demographics("X")

    @pytest.mark.asyncio
    async def test_get_patient_demographics_403_raises_auth_error(self):
        from app.services.fhir_service import FHIRAuthenticationError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/Patient/X").mock(
                return_value=httpx.Response(403, json={"error": "Forbidden"})
            )
            with pytest.raises(FHIRAuthenticationError):
                await svc.get_patient_demographics("X")

    @pytest.mark.asyncio
    async def test_get_patient_demographics_404_raises_not_found(self):
        from app.services.fhir_service import FHIRResourceNotFoundError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/Patient/GHOST").mock(
                return_value=httpx.Response(404, json={"error": "Not Found"})
            )
            with pytest.raises(FHIRResourceNotFoundError):
                await svc.get_patient_demographics("GHOST")

    @pytest.mark.asyncio
    async def test_get_patient_demographics_500_raises_connection_error(self):
        from app.services.fhir_service import FHIRConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/Patient/P").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )
            with pytest.raises(FHIRConnectionError):
                await svc.get_patient_demographics("P")

    @pytest.mark.asyncio
    async def test_get_patient_demographics_timeout_raises_connection_error(self):
        from app.services.fhir_service import FHIRConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/Patient/P").mock(
                side_effect=httpx.TimeoutException("timeout")
            )
            with pytest.raises(FHIRConnectionError):
                await svc.get_patient_demographics("P")

    # get_active_medications
    @pytest.mark.asyncio
    async def test_get_active_medications_success_returns_bundle(self):
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/MedicationRequest").mock(
                return_value=httpx.Response(200, json=_FHIR_BUNDLE_PAYLOAD)
            )
            bundle = await svc.get_active_medications("12724067")
        assert bundle.resourceType == "Bundle"
        assert len(bundle.entry) == 1

    @pytest.mark.asyncio
    async def test_get_active_medications_401_raises_auth_error(self):
        from app.services.fhir_service import FHIRAuthenticationError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/MedicationRequest").mock(
                return_value=httpx.Response(401, json={"error": "Unauthorized"})
            )
            with pytest.raises(FHIRAuthenticationError):
                await svc.get_active_medications("12724067")

    @pytest.mark.asyncio
    async def test_get_active_medications_500_raises_connection_error(self):
        from app.services.fhir_service import FHIRConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/MedicationRequest").mock(
                return_value=httpx.Response(500, text="Server Error")
            )
            with pytest.raises(FHIRConnectionError):
                await svc.get_active_medications("12724067")

    @pytest.mark.asyncio
    async def test_get_active_medications_timeout_raises_connection_error(self):
        from app.services.fhir_service import FHIRConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{FHIR_BASE}/MedicationRequest").mock(
                side_effect=httpx.TimeoutException("timeout")
            )
            with pytest.raises(FHIRConnectionError):
                await svc.get_active_medications("12724067")

    @pytest.mark.asyncio
    async def test_get_active_medications_empty_bundle_is_valid(self):
        svc = self._service()
        empty_bundle = {"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []}
        with respx.mock:
            respx.get(f"{FHIR_BASE}/MedicationRequest").mock(
                return_value=httpx.Response(200, json=empty_bundle)
            )
            bundle = await svc.get_active_medications("P_NO_MEDS")
        assert bundle.total == 0
        assert bundle.entry == []

    # Authorization header
    def test_authorization_header_uses_bearer_token(self):
        svc = self._service()
        headers = svc._get_headers()
        assert headers["Authorization"] == f"Bearer {FHIR_TOKEN}"
        assert "application/fhir+json" in headers["Accept"]
