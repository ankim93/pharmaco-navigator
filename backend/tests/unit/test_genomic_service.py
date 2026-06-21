"""
Unit tests for app/services/genomic_service.py — DB calls mocked via AsyncMock.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Shared helpers
class _MockGenotypeRecord:
    def __init__(self, patient_id, gene, allele_1, allele_2):
        self.patient_id = patient_id
        self.gene_symbol = gene
        self.allele_1 = allele_1
        self.allele_2 = allele_2


def _make_async_db_session(records):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = records
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_cm)
    return mock_session, mock_factory


# Tests
@pytest.mark.unit
class TestGenomicService:

    def _service(self):
        from app.services.genomic_service import GenomicService
        return GenomicService()

    @pytest.mark.asyncio
    async def test_get_patient_genotypes_all_four_genes(self):
        """
        Returns dict with all 4 supported genes when DB has full records.
        """
        svc = self._service()
        records = [
            _MockGenotypeRecord("P1", "CYP2D6",  "*1",  "*4"),
            _MockGenotypeRecord("P1", "CYP2C19", "*1",  "*2"),
            _MockGenotypeRecord("P1", "SLCO1B1", "*1",  "*5"),
            _MockGenotypeRecord("P1", "ABCB1",   "C",   "T"),
        ]
        _, mock_factory = _make_async_db_session(records)
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            result = await svc.get_patient_genotypes("P1")

        assert result["CYP2D6"]  == ("*1", "*4")
        assert result["CYP2C19"] == ("*1", "*2")
        assert result["SLCO1B1"] == ("*1", "*5")
        assert result["ABCB1"]   == ("C",  "T")

    @pytest.mark.asyncio
    async def test_get_patient_genotypes_missing_genes_marked_missing(self):
        """
        Genes absent from DB are set to the string 'Missing'.
        """
        svc = self._service()
        records = [
            _MockGenotypeRecord("P2", "CYP2D6", "*1", "*1"),
        ]
        _, mock_factory = _make_async_db_session(records)
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            result = await svc.get_patient_genotypes("P2")

        assert result["CYP2D6"]  == ("*1", "*1")
        assert result["CYP2C19"] == "Missing"
        assert result["SLCO1B1"] == "Missing"
        assert result["ABCB1"]   == "Missing"

    @pytest.mark.asyncio
    async def test_get_patient_genotypes_empty_patient_id_raises_validation_error(self):
        from app.services.genomic_service import GenomicValidationError
        svc = self._service()
        with pytest.raises(GenomicValidationError):
            await svc.get_patient_genotypes("")

    @pytest.mark.asyncio
    async def test_get_patient_genotypes_all_missing_raises_data_not_found(self):
        """
        All four genes missing -> GenomicDataNotFoundError (no 500).
        """
        from app.services.genomic_service import GenomicDataNotFoundError
        svc = self._service()
        _, mock_factory = _make_async_db_session([])  # no records at all
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            with pytest.raises(GenomicDataNotFoundError):
                await svc.get_patient_genotypes("NO_DATA_PATIENT")

    @pytest.mark.asyncio
    async def test_get_patient_genotypes_db_error_raises_connection_error(self):
        from app.services.genomic_service import GenomicConnectionError
        from sqlalchemy.exc import SQLAlchemyError
        svc = self._service()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("DB down"))
        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)
        mock_factory = MagicMock(return_value=mock_session_cm)

        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            with pytest.raises(GenomicConnectionError):
                await svc.get_patient_genotypes("P3")

    @pytest.mark.asyncio
    async def test_get_patient_genotypes_required_genes_subset(self):
        """
        required_genes parameter restricts which genes are queried.
        """
        svc = self._service()
        records = [
            _MockGenotypeRecord("P4", "CYP2D6",  "*4", "*4"),
            _MockGenotypeRecord("P4", "CYP2C19", "*1", "*2"),
        ]
        _, mock_factory = _make_async_db_session(records)
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            result = await svc.get_patient_genotypes("P4", required_genes=["CYP2D6"])

        assert "CYP2D6"  in result
        assert "CYP2C19" not in result
