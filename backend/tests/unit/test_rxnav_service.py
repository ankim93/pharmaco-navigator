"""
Unit tests for app/services/rxnav_service.py — HTTP interactions mocked via respx.
"""

import pytest
import httpx
import respx

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"


@pytest.mark.unit
class TestRxNavService:

    def _service(self):
        from app.services.rxnav_service import RxNavService
        return RxNavService(base_url=RXNAV_BASE)

    # _find_approximate_rxcui
    @pytest.mark.asyncio
    async def test_find_approximate_rxcui_success(self):
        svc = self._service()
        payload = {"approximateGroup": {"candidate": [{"rxcui": "2670", "score": "100"}]}}
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/approximateTerm.json").mock(
                return_value=httpx.Response(200, json=payload)
            )
            respx.get(f"{RXNAV_BASE}/rxcui/2670/related.json").mock(
                return_value=httpx.Response(200, json={
                    "relatedGroup": {
                        "conceptGroup": [
                            {"tty": "IN", "conceptProperties": [{"rxcui": "2670"}]}
                        ]
                    }
                })
            )
            rxcui = await svc.get_rxcui_for_medication("Codeine")
        assert rxcui == "2670"

    @pytest.mark.asyncio
    async def test_find_approximate_rxcui_no_candidates_raises_not_found(self):
        from app.services.rxnav_service import RxNavNotFoundError
        svc = self._service()
        payload = {"approximateGroup": {"candidate": []}}
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/approximateTerm.json").mock(
                return_value=httpx.Response(200, json=payload)
            )
            with pytest.raises(RxNavNotFoundError):
                await svc._find_approximate_rxcui("UnknownMed")

    @pytest.mark.asyncio
    async def test_find_approximate_rxcui_missing_candidate_key_raises_not_found(self):
        from app.services.rxnav_service import RxNavNotFoundError
        svc = self._service()
        payload = {"approximateGroup": {}}
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/approximateTerm.json").mock(
                return_value=httpx.Response(200, json=payload)
            )
            with pytest.raises(RxNavNotFoundError):
                await svc._find_approximate_rxcui("SomeMed")

    @pytest.mark.asyncio
    async def test_find_approximate_rxcui_missing_rxcui_field_raises_error(self):
        from app.services.rxnav_service import RxNavValidationError
        svc = self._service()
        payload = {"approximateGroup": {"candidate": [{"score": "100"}]}}
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/approximateTerm.json").mock(
                return_value=httpx.Response(200, json=payload)
            )
            with pytest.raises((RxNavValidationError, Exception)):
                await svc._find_approximate_rxcui("SomeMed")

    @pytest.mark.asyncio
    async def test_find_approximate_rxcui_server_error_raises_connection_error(self):
        from app.services.rxnav_service import RxNavConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/approximateTerm.json").mock(
                return_value=httpx.Response(503, text="Service Unavailable")
            )
            with pytest.raises(RxNavConnectionError):
                await svc._find_approximate_rxcui("Codeine")

    @pytest.mark.asyncio
    async def test_find_approximate_rxcui_timeout_raises_connection_error(self):
        from app.services.rxnav_service import RxNavConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/approximateTerm.json").mock(
                side_effect=httpx.TimeoutException("timeout")
            )
            with pytest.raises(RxNavConnectionError):
                await svc._find_approximate_rxcui("Codeine")

    @pytest.mark.asyncio
    async def test_find_approximate_rxcui_connect_error_raises_connection_error(self):
        from app.services.rxnav_service import RxNavConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/approximateTerm.json").mock(
                side_effect=httpx.ConnectError("refused")
            )
            with pytest.raises(RxNavConnectionError):
                await svc._find_approximate_rxcui("Codeine")

    # _get_ingredient_rxcui
    @pytest.mark.asyncio
    async def test_get_ingredient_rxcui_extracts_in_group(self):
        svc = self._service()
        payload = {
            "relatedGroup": {
                "conceptGroup": [
                    {"tty": "SBD", "conceptProperties": []},
                    {"tty": "IN",  "conceptProperties": [{"rxcui": "1049502"}]},
                ]
            }
        }
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/rxcui/2670/related.json").mock(
                return_value=httpx.Response(200, json=payload)
            )
            result = await svc._get_ingredient_rxcui("2670")
        assert result == "1049502"

    @pytest.mark.asyncio
    async def test_get_ingredient_rxcui_no_related_group_falls_back(self):
        svc = self._service()
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/rxcui/2670/related.json").mock(
                return_value=httpx.Response(200, json={})
            )
            respx.get(f"{RXNAV_BASE}/rxcui/2670/property.json").mock(
                return_value=httpx.Response(200, json={
                    "propConceptGroup": {
                        "propConcept": [{"propValue": "IN"}]
                    }
                })
            )
            result = await svc._get_ingredient_rxcui("2670")
        assert result == "2670"

    # _verify_ingredient_type
    @pytest.mark.asyncio
    async def test_verify_ingredient_type_is_in_returns_rxcui(self):
        svc = self._service()
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/rxcui/9999/property.json").mock(
                return_value=httpx.Response(200, json={
                    "propConceptGroup": {"propConcept": [{"propValue": "IN"}]}
                })
            )
            result = await svc._verify_ingredient_type("9999")
        assert result == "9999"

    @pytest.mark.asyncio
    async def test_verify_ingredient_type_not_in_raises_not_found(self):
        from app.services.rxnav_service import RxNavNotFoundError
        svc = self._service()
        with respx.mock:
            respx.get(f"{RXNAV_BASE}/rxcui/9999/property.json").mock(
                return_value=httpx.Response(200, json={
                    "propConceptGroup": {"propConcept": [{"propValue": "SBD"}]}
                })
            )
            with pytest.raises(RxNavNotFoundError):
                await svc._verify_ingredient_type("9999")
