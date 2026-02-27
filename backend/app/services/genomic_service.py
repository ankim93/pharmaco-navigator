"""
Genomic Data Service for Azure PostgreSQL integration.
Retrieves patient star-allele genotypes from the Azure-hosted genotypes table for pharmacogenomic screening.
"""

import logging
from typing import Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.models.genotype import Genotype
from app.db.session import async_session_factory


# Configure logging
logger = logging.getLogger(__name__)


# Custom Exceptions (Graceful Failure)
class GenomicServiceError(Exception):
    """
    Base exception for genomic service errors.
    """
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class GenomicConnectionError(GenomicServiceError):
    """
    Raised when database connection fails.
    """
    pass


class GenomicDataNotFoundError(GenomicServiceError):
    """
    Raised when no genomic data exists for the patient.
    """
    pass


class GenomicValidationError(GenomicServiceError):
    """
    Raised when genomic data validation fails.
    """
    pass


# GenomicService Class
class GenomicService:
    """
    Asynchronous service for retrieving patient genotype data from Azure PostgreSQL.
    """
    
    # High-impact pharmacogenes
    SUPPORTED_GENES = ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]
    
    def __init__(self) -> None:
        """
        Initialize GenomicService.
        """
        logger.info("GenomicService initialized")
    
    async def get_patient_genotypes(
        self,
        patient_id: str,
        required_genes: Optional[list[str]] = None
    ) -> Dict[str, Tuple[str, str] | str]:
        """
        Retrieve all genotypes for a patient from Azure PostgreSQL.
        """
        # Validate patient_id
        if not patient_id or not patient_id.strip():
            raise GenomicValidationError(
                message="Patient ID is required",
                details="patient_id cannot be empty or whitespace"
            )
        
        # Determine which genes to query
        genes_to_query = required_genes or self.SUPPORTED_GENES
        
        logger.info(
            f"Retrieving genotypes for patient_id='{patient_id}', "
            f"genes={genes_to_query}"
        )
        
        try:
            # Execute async database query
            async with async_session_factory() as session:
                # Query all genotypes for the patient
                stmt = select(Genotype).where(Genotype.patient_id == patient_id) # type: ignore[arg-type]
                result = await session.execute(stmt)
                genotype_records = result.scalars().all()
                
                logger.info(
                    f"Found {len(genotype_records)} genotype records for "
                    f"patient_id='{patient_id}'"
                )
                
                # Build result dictionary
                genotype_dict: Dict[str, Tuple[str, str] | str] = {}
                
                # Map retrieved genotypes
                for record in genotype_records:
                    if record.gene_symbol in genes_to_query:
                        genotype_dict[record.gene_symbol] = (
                            record.allele_1,
                            record.allele_2
                        )
                        logger.debug(
                            f"Mapped {record.gene_symbol}: "
                            f"({record.allele_1}, {record.allele_2})"
                        )
                
                # Mark missing genes as 'Missing'
                for gene in genes_to_query:
                    if gene not in genotype_dict:
                        genotype_dict[gene] = "Missing"
                        logger.warning(
                            f"Gene {gene} not found for patient_id='{patient_id}' "
                            f"- marked as 'Missing' for Grey status"
                        )
                
                # Check if patient has ANY genomic data
                if all(value == "Missing" for value in genotype_dict.values()):
                    raise GenomicDataNotFoundError(
                        message=f"No genomic data found for patient_id='{patient_id}'",
                        details=(
                            "The genotypes table contains no records for this patient. "
                            "Clinical action required: Order pharmacogenomic testing."
                        )
                    )
                
                logger.info(
                    f"Successfully retrieved genotypes for patient_id='{patient_id}': "
                    f"{list(genotype_dict.keys())}"
                )
                
                return genotype_dict
        
        except GenomicDataNotFoundError:
            # Re-raise custom exception without wrapping
            raise
        
        except SQLAlchemyError as e:
            # Database connection or query execution error
            logger.error(
                f"Database error retrieving genotypes for patient_id='{patient_id}': {e}",
                exc_info=True
            )
            raise GenomicConnectionError(
                message="Failed to query genomic database",
                details=f"SQLAlchemy error: {str(e)}"
            )
        
        except Exception as e:
            # Unexpected error
            logger.error(
                f"Unexpected error in get_patient_genotypes for patient_id='{patient_id}': {e}",
                exc_info=True
            )
            raise GenomicServiceError(
                message="Unexpected error retrieving genomic data",
                details=str(e)
            )
    
    async def get_gene_for_patient(
        self,
        patient_id: str,
        gene_symbol: str
    ) -> Optional[Tuple[str, str]]:
        """
        Retrieve a single gene's allele pair for a patient.
        """
        # Validate inputs
        if not patient_id or not patient_id.strip():
            raise GenomicValidationError(
                message="Patient ID is required",
                details="patient_id cannot be empty"
            )
        
        if not gene_symbol or not gene_symbol.strip():
            raise GenomicValidationError(
                message="Gene symbol is required",
                details="gene_symbol cannot be empty"
            )
        
        logger.info(
            f"Retrieving {gene_symbol} genotype for patient_id='{patient_id}'"
        )
        
        try:
            async with async_session_factory() as session:
                # Query specific gene for patient
                stmt = select(Genotype).where(
                    Genotype.patient_id == patient_id,  # type: ignore[arg-type]
                    Genotype.gene_symbol == gene_symbol # type: ignore[arg-type]
                )
                result = await session.execute(stmt)
                genotype_record = result.scalar_one_or_none()
                
                if genotype_record:
                    logger.info(
                        f"Found {gene_symbol} for patient_id='{patient_id}': "
                        f"({genotype_record.allele_1}, {genotype_record.allele_2})"
                    )
                    return (genotype_record.allele_1, genotype_record.allele_2)
                else:
                    logger.warning(
                        f"Gene {gene_symbol} not found for patient_id='{patient_id}'"
                    )
                    return None
        
        except SQLAlchemyError as e:
            logger.error(
                f"Database error retrieving {gene_symbol} for patient_id='{patient_id}': {e}",
                exc_info=True
            )
            raise GenomicConnectionError(
                message=f"Failed to query {gene_symbol} genotype",
                details=f"SQLAlchemy error: {str(e)}"
            )
        
        except Exception as e:
            logger.error(
                f"Unexpected error in get_gene_for_patient: {e}",
                exc_info=True
            )
            raise GenomicServiceError(
                message="Unexpected error retrieving gene data",
                details=str(e)
            )
    
    async def check_patient_has_data(self, patient_id: str) -> bool:
        """
        Check if any genomic data exists for a patient.
        """
        logger.info(f"Checking for genomic data for patient_id='{patient_id}'")
        
        try:
            async with async_session_factory() as session:
                stmt = select(Genotype).where(Genotype.patient_id == patient_id).limit(1)   # type: ignore[arg-type]
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                
                has_data = record is not None
                logger.info(
                    f"Patient '{patient_id}' has genomic data: {has_data}"
                )
                return has_data
        
        except SQLAlchemyError as e:
            logger.error(
                f"Database error checking patient data: {e}",
                exc_info=True
            )
            raise GenomicConnectionError(
                message="Failed to check patient genomic data",
                details=f"SQLAlchemy error: {str(e)}"
            )


# Factory Function
def create_genomic_service() -> GenomicService:
    """
    Factory function to create a GenomicService instance.
    """
    return GenomicService()
