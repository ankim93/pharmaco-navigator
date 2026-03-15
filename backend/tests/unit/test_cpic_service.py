"""
Unit tests for app/services/cpic_service.py — HTTP interactions mocked via respx.
"""

import pytest
import httpx
import respx

CPIC_BASE = "https://api.cpicpgx.org/v1"


def _make_cpic_response(
    drug="Codeine",
    recommendation="Avoid codeine use. Use alternative analgesic.",
    classification="Strong",
    level="A",
    gene="CYP2D6",
    phenotype="Poor Metabolizer",
):
    return [
        {
            "drugname": drug,
            "recommendation": recommendation,
            "classification": classification,
            "guideline": {
                "level": level,
                "url": f"https://cpicpgx.org/guidelines/guideline-for-{drug.lower()}/",
            },
            "genesymbol": gene,
            "phenotype": phenotype,
        }
    ]


@pytest.mark.unit
class TestCPICService:

    def _service(self):
        from app.services.cpic_service import CPICService
        return CPICService()

    # fetch_recommendations
    @pytest.mark.asyncio
    async def test_fetch_recommendations_success_level_a(self):
        svc = self._service()
        payload = _make_cpic_response(drug="Codeine", level="A")
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                return_value=httpx.Response(200, json=payload)
            )
            recs = await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")
        assert len(recs) == 1
        assert recs[0].drug_name == "Codeine"
        assert recs[0].guideline_level == "A"

    @pytest.mark.asyncio
    async def test_fetch_recommendations_success_level_b(self):
        svc = self._service()
        payload = _make_cpic_response(level="B", drug="Amitriptyline")
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                return_value=httpx.Response(200, json=payload)
            )
            recs = await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")
        assert len(recs) == 1
        assert recs[0].guideline_level == "B"

    @pytest.mark.asyncio
    async def test_fetch_recommendations_filters_level_c(self):
        from app.services.cpic_service import CPICDataNotFoundError
        svc = self._service()
        payload = _make_cpic_response(level="C")
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                return_value=httpx.Response(200, json=payload)
            )
            with pytest.raises(CPICDataNotFoundError):
                await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")

    @pytest.mark.asyncio
    async def test_fetch_recommendations_empty_response_raises_not_found(self):
        from app.services.cpic_service import CPICDataNotFoundError
        svc = self._service()
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                return_value=httpx.Response(200, json=[])
            )
            with pytest.raises(CPICDataNotFoundError):
                await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")

    @pytest.mark.asyncio
    async def test_fetch_recommendations_http_404_raises_api_error(self):
        from app.services.cpic_service import CPICAPIError
        svc = self._service()
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                return_value=httpx.Response(404, json={"error": "not found"})
            )
            with pytest.raises(CPICAPIError):
                await svc.fetch_recommendations("FAKEGENE", "Unknown")

    @pytest.mark.asyncio
    async def test_fetch_recommendations_http_500_raises_api_error(self):
        from app.services.cpic_service import CPICAPIError
        svc = self._service()
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                return_value=httpx.Response(500, text="Internal Server Error")
            )
            with pytest.raises(CPICAPIError):
                await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")

    @pytest.mark.asyncio
    async def test_fetch_recommendations_timeout_raises_connection_error(self):
        from app.services.cpic_service import CPICConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                side_effect=httpx.TimeoutException("timeout")
            )
            with pytest.raises(CPICConnectionError):
                await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")

    @pytest.mark.asyncio
    async def test_fetch_recommendations_connect_error_raises_connection_error(self):
        from app.services.cpic_service import CPICConnectionError
        svc = self._service()
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                side_effect=httpx.ConnectError("refused")
            )
            with pytest.raises(CPICConnectionError):
                await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")

    @pytest.mark.asyncio
    async def test_fetch_recommendations_multiple_only_a_and_b_returned(self):
        svc = self._service()
        payload = [
            _make_cpic_response(drug="Codeine",    level="A")[0],
            _make_cpic_response(drug="Tramadol",   level="B")[0],
            _make_cpic_response(drug="Hydrocodone",level="C")[0],
        ]
        with respx.mock:
            respx.get(f"{CPIC_BASE}/recommendation").mock(
                return_value=httpx.Response(200, json=payload)
            )
            recs = await svc.fetch_recommendations("CYP2D6", "Poor Metabolizer")
        names = {r.drug_name for r in recs}
        assert len(recs) == 2
        assert "Codeine" in names
        assert "Tramadol" in names
        assert "Hydrocodone" not in names

    # fetch_gene_substrates
    @pytest.mark.asyncio
    async def test_fetch_gene_substrates_returns_drug_list(self):
        svc = self._service()
        pair_payload = [
            {"drugname": "Codeine"},
            {"drugname": "Tramadol"},
            {"drugname": "Metoprolol"},
        ]
        with respx.mock:
            respx.get(f"{CPIC_BASE}/pair").mock(
                return_value=httpx.Response(200, json=pair_payload)
            )
            substrates = await svc.fetch_gene_substrates("CYP2D6")
        assert isinstance(substrates, list)
        assert any(s.lower() == "codeine" for s in substrates)

    @pytest.mark.asyncio
    async def test_fetch_gene_substrates_empty_response_returns_empty_list(self):
        svc = self._service()
        with respx.mock:
            respx.get(f"{CPIC_BASE}/pair").mock(
                return_value=httpx.Response(200, json=[])
            )
            substrates = await svc.fetch_gene_substrates("CYP2D6")
        assert substrates == []
