"""
Unit tests for app/services/phenotype_service.py.
"""

import pytest
from unittest.mock import AsyncMock


# 1. calculate_score
@pytest.mark.unit
class TestPhenotypeServiceCalculateScore:
    """
    Unit tests for PhenotypeService.calculate_score.
    """
    def _service(self):
        from app.services.phenotype_service import PhenotypeService
        return PhenotypeService()

    @pytest.mark.parametrize("alleles,expected", [
        (("*1",  "*1"),  2.0),   # 1.0 + 1.0 = Normal
        (("*1",  "*4"),  1.0),   # 1.0 + 0.0
        (("*4",  "*4"),  0.0),   # 0.0 + 0.0 = Poor
        (("*1",  "*10"), 1.25),  # 1.0 + 0.25
        (("*1",  "*17"), 1.5),   # 1.0 + 0.5
        (("*4",  "*10"), 0.25),  # 0.0 + 0.25 = Intermediate
        (("*2",  "*2"),  2.0),   # 1.0 + 1.0
        (("*1",  "*41"), 1.5),   # 1.0 + 0.5
        (("*5",  "*5"),  0.0),   # gene deletion × 2
    ])
    def test_cyp2d6_activity_scores(self, alleles, expected):
        svc = self._service()
        assert svc.calculate_score("CYP2D6", alleles) == expected

    @pytest.mark.parametrize("alleles,expected", [
        (("*1",  "*1"),  2.0),   # 1.0 + 1.0 = Normal
        (("*2",  "*2"),  0.0),   # 0.0 + 0.0 = Poor
        (("*1",  "*2"),  1.0),   # 1.0 + 0.0 = Intermediate
        (("*1",  "*17"), 2.0),   # 1.0 + 1.0 = Normal
        (("*17", "*17"), 2.0),   # 1.0 + 1.0 = Normal (not ultrarapid in CYP2C19 score table)
        (("*3",  "*3"),  0.0),   # 0.0 + 0.0 = Poor
    ])
    def test_cyp2c19_activity_scores(self, alleles, expected):
        svc = self._service()
        assert svc.calculate_score("CYP2C19", alleles) == expected

    def test_slco1b1_score_is_none(self):
        svc = self._service()
        assert svc.calculate_score("SLCO1B1", ("*1", "*5")) is None

    def test_abcb1_score_is_none(self):
        svc = self._service()
        assert svc.calculate_score("ABCB1", ("C", "T")) is None

    def test_unknown_allele_uses_default_score(self):
        """
        Unknown star alleles should use the gene's default Activity Score.
        """
        svc = self._service()
        score = svc.calculate_score("CYP2D6", ("*UNKNOWN", "*1"))
        # *UNKNOWN defaults to CYP2D6_DEFAULT_SCORE (1.0), so total = 1.0 + 1.0 = 2.0
        assert score == 2.0


# 2. translate_phenotype
@pytest.mark.unit
class TestPhenotypeServiceTranslate:
    """
    Unit tests for PhenotypeService.translate_phenotype — every mapping.
    """
    def _service(self):
        from app.services.phenotype_service import PhenotypeService
        return PhenotypeService()

    @pytest.mark.parametrize("alleles,score,expected", [
        (("*4",  "*4"),  0.0,  "Poor Metabolizer"),
        (("*1",  "*10"), 1.25, "Normal Metabolizer"),
        (("*1",  "*4"),  1.0,  "Intermediate Metabolizer"),
        (("*1",  "*1"),  2.0,  "Normal Metabolizer"),
        (("*1",  "*17"), 1.5,  "Normal Metabolizer"),
    ])
    def test_cyp2d6_phenotype(self, alleles, score, expected):
        svc = self._service()
        assert svc.translate_phenotype("CYP2D6", alleles, score) == expected

    @pytest.mark.parametrize("alleles,score,expected", [
        (("*2",  "*2"),  0.0, "Poor Metabolizer"),
        (("*1",  "*2"),  1.0, "Intermediate Metabolizer"),
        (("*1",  "*1"),  2.0, "Normal Metabolizer"),
        (("*17", "*17"), 2.0, "Normal Metabolizer"),
    ])
    def test_cyp2c19_phenotype(self, alleles, score, expected):
        svc = self._service()
        assert svc.translate_phenotype("CYP2C19", alleles, score) == expected

    @pytest.mark.parametrize("alleles,expected", [
        (("*1",   "*1"),  "Normal Function"),
        (("*1",   "*5"),  "Decreased Function"),
        (("*5",   "*5"),  "Poor Function"),
        (("*5",   "*15"), "Poor Function"),
    ])
    def test_slco1b1_phenotype(self, alleles, expected):
        svc = self._service()
        assert svc.translate_phenotype("SLCO1B1", alleles, None) == expected

    @pytest.mark.parametrize("alleles,expected", [
        (("C",  "C"),   "Normal Transport Function"),
        (("C",  "T"),   "Intermediate Transport Function"),
        (("T",  "T"),   "Reduced Transport Function"),
        (("*1", "*2"),  "Intermediate Transport Function"),
    ])
    def test_abcb1_phenotype(self, alleles, expected):
        svc = self._service()
        assert svc.translate_phenotype("ABCB1", alleles, None) == expected


# 3. get_clinical_profile
@pytest.mark.unit
class TestPhenotypeServiceGetClinicalProfile:
    """
    Tests for PhenotypeService.get_clinical_profile (async).
    """
    def _service_with_genomic(self, genotype_return_value=None, side_effect=None):
        from app.services.phenotype_service import PhenotypeService
        from app.services.genomic_service import GenomicService
        mock_genomic_svc = AsyncMock(spec=GenomicService)
        if side_effect:
            mock_genomic_svc.get_patient_genotypes = AsyncMock(side_effect=side_effect)
        else:
            mock_genomic_svc.get_patient_genotypes = AsyncMock(return_value=genotype_return_value)
        return PhenotypeService(genomic_service=mock_genomic_svc)

    @pytest.mark.asyncio
    async def test_get_clinical_profile_normal_patient(self):
        genotypes = {
            "CYP2D6":  ("*1", "*1"),
            "CYP2C19": ("*1", "*1"),
            "SLCO1B1": ("*1", "*1"),
            "ABCB1":   ("C",  "C"),
        }
        svc = self._service_with_genomic(genotypes)
        profile = await svc.get_clinical_profile("DEMO002")

        assert profile["CYP2D6"]["phenotype"]  == "Normal Metabolizer"
        assert profile["CYP2D6"]["data_available"] is True
        assert profile["SLCO1B1"]["phenotype"] == "Normal Function"
        assert profile["ABCB1"]["phenotype"]   == "Normal Transport Function"

    @pytest.mark.asyncio
    async def test_get_clinical_profile_poor_metabolizer(self):
        genotypes = {
            "CYP2D6":  ("*4", "*4"),
            "CYP2C19": ("*2", "*2"),
            "SLCO1B1": ("*1", "*1"),
            "ABCB1":   ("C",  "C"),
        }
        svc = self._service_with_genomic(genotypes)
        profile = await svc.get_clinical_profile("DEMO001")

        assert profile["CYP2D6"]["phenotype"]  == "Poor Metabolizer"
        assert profile["CYP2C19"]["phenotype"] == "Poor Metabolizer"

    @pytest.mark.asyncio
    async def test_get_clinical_profile_missing_gene_data_available_false(self):
        """
        Any gene set to 'Missing' must yield data_available=False in the profile.
        """
        genotypes = {
            "CYP2D6":  ("*1", "*4"),
            "CYP2C19": "Missing",
            "SLCO1B1": "Missing",
            "ABCB1":   ("C",  "T"),
        }
        svc = self._service_with_genomic(genotypes)
        profile = await svc.get_clinical_profile("P_PARTIAL")

        assert profile["CYP2D6"]["data_available"]  is True
        assert profile["CYP2C19"]["data_available"] is False
        assert profile["CYP2C19"]["phenotype"]      == "Data Missing/Unknown"
        assert profile["SLCO1B1"]["data_available"] is False

    @pytest.mark.asyncio
    async def test_get_clinical_profile_tc04_all_genes_missing_returns_grey_profile(self):
        """
        TC-04: Patient has NO genomic data in the database.
        PhenotypeService must return data_available=False for all genes
        instead of raising an exception.
        """
        from app.services.genomic_service import GenomicDataNotFoundError
        svc = self._service_with_genomic(
            side_effect=GenomicDataNotFoundError("No genomic data", "test")
        )
        profile = await svc.get_clinical_profile("DEMO007")

        # All four core genes should be present with data_available=False
        assert len(profile) == 4
        for gene in ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]:
            assert profile[gene]["data_available"] is False
            assert profile[gene]["phenotype"] == "Data Missing/Unknown"
