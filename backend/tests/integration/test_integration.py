"""
Integration tests for the PharmacoNavigator recommendation pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any


# Module-level helpers (shared across TC classes)
def _mock_demo_bundle(medication_names: list):
    """
    Build a minimal FHIRBundle containing the supplied medication names.
    """
    from app.models.schemas import (
        FHIRBundle,
        FHIRBundleEntry,
        FHIRMedicationRequest,
        FHIRCodeableConcept,
        FHIRReference,
    )
    entries = []
    for name in medication_names:
        med_req = FHIRMedicationRequest(
            resourceType="MedicationRequest",
            id=f"mock-{name.lower()}",
            status="active",
            intent="order",
            medicationCodeableConcept=FHIRCodeableConcept(
                coding=[{"system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                         "code": "demo", "display": name}],
                text=name,
            ),
            subject=FHIRReference(reference="Patient/MOCK", display="Mock Patient"),
            authoredOn=None,
        )
        entries.append(FHIRBundleEntry(
            fullUrl=f"https://mock.fhir/MedicationRequest/{med_req.id}",
            resource=med_req.model_dump(),
        ))
    return FHIRBundle(
        resourceType="Bundle",
        type="searchset",
        total=len(medication_names),
        entry=entries,
    )


def _build_service(
    phenotype_profile: Dict[str, Any],
    cpic_recs_by_gene: Dict[str, list] | None = None,
):
    """
    Factory: assembles a RecommendationService with all dependencies mocked.
    """
    from app.services.recommendation_service import RecommendationService
    from app.services.phenotype_service import PhenotypeService
    from app.services.cpic_service import CPICService, CPICDataNotFoundError

    mock_phenotype_svc = AsyncMock(spec=PhenotypeService)
    mock_phenotype_svc.get_clinical_profile = AsyncMock(return_value=phenotype_profile)

    mock_cpic_svc = AsyncMock(spec=CPICService)
    cpic_recs_by_gene = cpic_recs_by_gene or {}

    async def _cpic_fetch(gene, phenotype):
        recs = cpic_recs_by_gene.get(gene)
        if not recs:
            raise CPICDataNotFoundError(f"No recs for {gene}")
        return recs

    async def _cpic_substrates(gene):
        substrate_map = {
            "CYP2D6":  ["Codeine", "Tramadol", "Metoprolol", "Amitriptyline"],
            "CYP2C19": ["Clopidogrel", "Omeprazole", "Citalopram"],
            "SLCO1B1": ["Simvastatin", "Atorvastatin"],
            "ABCB1":   ["Digoxin"],
        }
        return substrate_map.get(gene, [])

    mock_cpic_svc.fetch_recommendations = AsyncMock(side_effect=_cpic_fetch)
    mock_cpic_svc.fetch_gene_substrates  = AsyncMock(side_effect=_cpic_substrates)

    return RecommendationService(
        phenotype_service=mock_phenotype_svc,
        cpic_service=mock_cpic_svc,
    )


def _poor_cyp2d6_profile() -> Dict[str, Any]:
    return {
        "CYP2D6":  {"data_available": True, "phenotype": "Poor Metabolizer",
                    "allele_1": "*4", "allele_2": "*4", "activity_score": 0.0},
        "CYP2C19": {"data_available": True, "phenotype": "Normal Metabolizer",
                    "allele_1": "*1", "allele_2": "*1", "activity_score": 2.0},
        "SLCO1B1": {"data_available": True, "phenotype": "Normal Function",
                    "allele_1": "*1", "allele_2": "*1", "activity_score": None},
        "ABCB1":   {"data_available": True, "phenotype": "Normal Transport Function",
                    "allele_1": "C", "allele_2": "C", "activity_score": None},
    }


def _all_missing_profile() -> Dict[str, Any]:
    profile = {}
    for gene in ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]:
        profile[gene] = {
            "data_available": False,
            "phenotype": "Data Missing/Unknown",
            "allele_1": None, "allele_2": None, "activity_score": None,
        }
    return profile


# TC2 - Genomic Profile Retrieval & Phenotype Calculation
@pytest.mark.integration
class TestTC2GenomicProfileRetrieval:
    """
    TC2: The system retrieves star-allele genotypes from the database, calculates
    Activity Scores, and translates them to CPIC phenotypes.
    """

    @pytest.mark.asyncio
    async def test_get_genomic_summary_returns_correct_structure(self):

        from app.services.recommendation_service import RecommendationService
        from app.services.phenotype_service import PhenotypeService
        from app.services.cpic_service import CPICService

        mock_phenotype_svc = AsyncMock(spec=PhenotypeService)
        mock_phenotype_svc.get_clinical_profile = AsyncMock(
            return_value=_poor_cyp2d6_profile()
        )
        svc = RecommendationService(
            phenotype_service=mock_phenotype_svc,
            cpic_service=AsyncMock(spec=CPICService),
        )
        summary = await svc.get_genomic_summary("DEMO001")

        assert summary.patient_id == "DEMO001"
        assert "CYP2D6" in summary.genes_analyzed
        assert len(summary.genes_missing) == 0
        assert summary.phenotypes["CYP2D6"] == "Poor Metabolizer"


# TC3 — RED Alert Generation (CYP2D6 Poor Metabolizer)
@pytest.mark.integration
class TestTC3RedAlertGeneration:
    """
    TC3: CYP2D6 Poor Metabolizer (*4/*4, Activity Score 0.0) combined with
    Codeine must produce a RED (High Risk) alert.
    """

    @pytest.mark.asyncio
    async def test_poor_cyp2d6_codeine_produces_red_alert(self):

        from app.services.cpic_service import CPICRecommendation
        from app.models.recommendation import ClinicalAlertResponse

        codeine_rec = CPICRecommendation(
            drug_name="Codeine",
            gene_symbol="CYP2D6",
            phenotype="Poor Metabolizer",
            recommendation="Avoid codeine use. Use alternative analgesic.",
            classification="Strong",
            guideline_url="https://cpicpgx.org/guidelines/guideline-for-codeine/",
            guideline_level="A",
        )
        svc = _build_service(
            phenotype_profile=_poor_cyp2d6_profile(),
            cpic_recs_by_gene={"CYP2D6": [codeine_rec]},
        )

        with patch(
            "app.services.recommendation_service.DemoFHIRService.is_demo_patient",
            return_value=True
        ), patch(
            "app.services.recommendation_service.DemoFHIRService.get_active_medications",
            return_value=_mock_demo_bundle(["Codeine"])
        ):
            response = await svc.generate_clinical_alerts("DEMO001")

        assert isinstance(response, ClinicalAlertResponse)
        assert response.patient_id == "DEMO001"
        assert len(response.red_alerts) >= 1
        assert any(r.drug_name == "Codeine" for r in response.red_alerts)


# TC4 — Missing Genomic Data -> GREY Alerts
@pytest.mark.integration
class TestTC4MissingDataGreyAlerts:
    """
    TC4: When a patient has missing genomic data the system must generate GREY
    alerts.
    """
    @pytest.mark.asyncio
    async def test_all_genes_missing_produces_grey_alerts_not_exception(self):
        """
        All four genes marked data_available=False -> service returns a valid
        ClinicalAlertResponse
        """
        from app.models.recommendation import ClinicalAlertResponse

        svc = _build_service(
            phenotype_profile=_all_missing_profile(),
            cpic_recs_by_gene={},
        )

        with patch(
            "app.services.recommendation_service.DemoFHIRService.is_demo_patient",
            return_value=True
        ), patch(
            "app.services.recommendation_service.DemoFHIRService.get_active_medications",
            return_value=_mock_demo_bundle(["Codeine", "Simvastatin"])
        ):
            response = await svc.generate_clinical_alerts("DEMO007")

        assert isinstance(response, ClinicalAlertResponse)
        assert len(response.grey_alerts) >= 4
        assert len(response.red_alerts)    == 0
        assert len(response.yellow_alerts) == 0
        assert len(response.green_alerts)  == 0

        grey_genes = {r.gene_symbol for r in response.grey_alerts}
        for gene in ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]:
            assert gene in grey_genes, f"Expected GREY alert for {gene}"


# TC5 — Database connection failure -> HTTP 503
@pytest.mark.integration
class TestTC5DatabaseConnectionFailure:
    """
    TC5: Azure PostgreSQL unavailable -> GenomicConnectionError
    propagates through RecommendationService and the API handler converts it
    to HTTP 503 Service Unavailable.
    """

    @pytest.mark.asyncio
    async def test_summary_endpoint_returns_503_on_db_failure(self):
        """
        GET /api/v1/patient/<id>/summary -> 503 when GenomicConnectionError raised.
        """
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.genomic_service import GenomicConnectionError

        with patch(
            "app.services.phenotype_service.PhenotypeService.get_clinical_profile",
            new_callable=AsyncMock,
            side_effect=GenomicConnectionError("Azure PostgreSQL unreachable"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/patient/DEMO001/summary")

        assert response.status_code == 503, (
            f"Expected 503 Service Unavailable on DB failure, got {response.status_code}"
        )
        body = response.json()
        assert "detail" in body
        detail = body["detail"].lower()
        assert "database" in detail or "unavailable" in detail or "genomic" in detail

    @pytest.mark.asyncio
    async def test_alerts_endpoint_returns_503_on_db_failure(self):
        """
        GET /api/v1/patient/<id>/alerts -> 503 when GenomicConnectionError raised.
        """
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.genomic_service import GenomicConnectionError

        with patch(
            "app.services.phenotype_service.PhenotypeService.get_clinical_profile",
            new_callable=AsyncMock,
            side_effect=GenomicConnectionError("Azure PostgreSQL unreachable"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/patient/DEMO001/alerts")

        assert response.status_code == 503, (
            f"Expected 503 Service Unavailable on DB failure, got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_db_failure_does_not_return_500(self):

        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.services.genomic_service import GenomicConnectionError

        with patch(
            "app.services.phenotype_service.PhenotypeService.get_clinical_profile",
            new_callable=AsyncMock,
            side_effect=GenomicConnectionError("Timeout"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                summary_resp = await client.get("/api/v1/patient/DEMO001/summary")
                alerts_resp  = await client.get("/api/v1/patient/DEMO001/alerts")

        assert summary_resp.status_code != 500
        assert alerts_resp.status_code  != 500