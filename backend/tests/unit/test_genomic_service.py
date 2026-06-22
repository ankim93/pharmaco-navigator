"""
Unit tests for app/services/genomic_service.py — DB calls mocked via AsyncMock.
"""

from unittest import result

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.genomic_service import GenomicService, GenomicValidationError, GenomicDataNotFoundError, GenomicConnectionError


# Shared helpers
class _MockGenotypeRecord:
    def __init__(self, patient_id, gene, allele_1, allele_2):
        self.patient_id = patient_id
        self.gene_symbol = gene
        self.allele_1 = allele_1
        self.allele_2 = allele_2


def _make_async_db_session(records, single_record=None):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = records
    mock_result.scalar_one_or_none.return_value = single_record
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
        _, mock_factory = _make_async_db_session([], single_record=None)  # no records at all
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

    @pytest.mark.asyncio
    async def test_get_gene_for_patient_success(self):
        """
        Verify clean star-allele tuple retrieval for an explicit patient biomarker.
        """
        svc = self._service()
        record = _MockGenotypeRecord("P5", "CYP2D6", "*1", "*4")
        _, mock_factory = _make_async_db_session(records=[], single_record=record)
        
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            result = await svc.get_gene_for_patient("P5", "CYP2D6")
            
        assert result == ("*1", "*4")


    @pytest.mark.asyncio
    async def test_get_gene_for_patient_missing(self):
        """
        Verify get_gene_for_patient returns None if the record does not exist.
        """
        svc = self._service()
        _, mock_factory = _make_async_db_session(records=[], single_record=None)
        
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            result = await svc.get_gene_for_patient("P6", "CYP2D6")
            
        assert result is None


    @pytest.mark.asyncio
    async def test_check_patient_has_data_true(self):
        """
        Verify check_patient_has_data returns True when rows exist.
        """
        svc = self._service()
        record = _MockGenotypeRecord("P7", "CYC2C19", "*1", "*1")
        _, mock_factory = _make_async_db_session(records=[], single_record=record)
        
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            has_data = await svc.check_patient_has_data("P7")
            
        assert has_data is True


    @pytest.mark.asyncio
    async def test_check_patient_has_data_false(self):
        """
        Verify check_patient_has_data returns False when no rows exist.
        """
        svc = self._service()
        _, mock_factory = _make_async_db_session(records=[], single_record=None)
        
        with patch("app.services.genomic_service.AsyncSessionLocal", mock_factory):
            has_data = await svc.check_patient_has_data("P8")
            
        assert has_data is False