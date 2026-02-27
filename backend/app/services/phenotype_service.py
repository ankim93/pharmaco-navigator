"""
Phenotype Translation Service.
Converts patient star-allele genotypes into standardized clinical phenotypes using CPIC Activity Score calculations and functional status mapping.
"""

import logging
from typing import Dict, Optional, Tuple, Any
from app.services.genomic_service import (
    GenomicService,
    create_genomic_service,
    GenomicConnectionError,
    GenomicDataNotFoundError,
)
from app.core.cpic_tables import (
    GENE_ALLELE_SCORES,
    GENE_DEFAULT_SCORES,
    GENE_PHENOTYPE_FUNCTIONS,
    METABOLIC_ENZYMES,
    TRANSPORTERS,
)


# Configure logging
logger = logging.getLogger(__name__)


# Custom Exceptions (Graceful Failure)
class PhenotypeServiceError(Exception):
    """
    Base exception for phenotype service errors.
    """
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class PhenotypeCalculationError(PhenotypeServiceError):
    """
    Raised when phenotype calculation fails.
    """
    pass


# Phenotype Profile Model
class PhenotypeProfile:
    """
    Structured phenotype profile for a single gene.
    """
    
    def __init__(
        self,
        gene: str,
        allele_1: Optional[str] = None,
        allele_2: Optional[str] = None,
        activity_score: Optional[float] = None,
        phenotype: str = "Data Missing/Unknown",
        data_available: bool = False
    ):
        self.gene = gene
        self.allele_1 = allele_1
        self.allele_2 = allele_2
        self.activity_score = activity_score
        self.phenotype = phenotype
        self.data_available = data_available
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API response.
        """
        return {
            "gene": self.gene,
            "allele_1": self.allele_1,
            "allele_2": self.allele_2,
            "activity_score": self.activity_score,
            "phenotype": self.phenotype,
            "data_available": self.data_available,
        }
    
    def __repr__(self) -> str:
        """
        String representation for debugging.
        """
        if self.data_available:
            return (
                f"PhenotypeProfile(gene='{self.gene}', "
                f"genotype={self.allele_1}/{self.allele_2}, "
                f"activity_score={self.activity_score}, "
                f"phenotype='{self.phenotype}')"
            )
        else:
            return (
                f"PhenotypeProfile(gene='{self.gene}', "
                f"phenotype='{self.phenotype}', "
                f"data_available=False)"
            )


# PhenotypeService Class
class PhenotypeService:
    """
    Asynchronous service for translating genotypes to clinical phenotypes.
    """
    
    def __init__(self, genomic_service: Optional[GenomicService] = None):
        """
        Initialize PhenotypeService.
        """
        self.genomic_service = genomic_service or create_genomic_service()
        logger.info("PhenotypeService initialized")
    
    def calculate_score(
        self,
        gene: str,
        alleles: Tuple[str, str]
    ) -> Optional[float]:
        """
        Calculate Activity Score for metabolic enzymes (CYP2D6, CYP2C19).
        """
        allele_1, allele_2 = alleles
        
        # Transporters use diplotype mapping, not Activity Scores
        if gene in TRANSPORTERS:
            logger.debug(
                f"{gene} is a transporter - no Activity Score calculated"
            )
            return None
        
        # Metabolic enzymes use Activity Score summation
        if gene not in GENE_ALLELE_SCORES:
            logger.warning(
                f"Gene {gene} not found in allele score tables - "
                f"cannot calculate Activity Score"
            )
            return None
        
        allele_score_table = GENE_ALLELE_SCORES[gene]
        default_score = GENE_DEFAULT_SCORES.get(gene, 1.0)
        
        # Get scores for each allele (use default if unknown)
        score_1 = allele_score_table.get(allele_1, default_score)
        score_2 = allele_score_table.get(allele_2, default_score)
        
        # Log warnings for unknown alleles
        if allele_1 not in allele_score_table:
            logger.warning(
                f"Unknown allele {gene} {allele_1} - using default score {default_score}"
            )
        if allele_2 not in allele_score_table:
            logger.warning(
                f"Unknown allele {gene} {allele_2} - using default score {default_score}"
            )
        
        # Calculate total Activity Score
        activity_score = score_1 + score_2
        
        logger.info(
            f"Calculated Activity Score for {gene}: "
            f"{allele_1} ({score_1}) + {allele_2} ({score_2}) = {activity_score}"
        )
        
        return activity_score
    
    def translate_phenotype(
        self,
        gene: str,
        alleles: Tuple[str, str],
        score: Optional[float] = None
    ) -> str:
        """
        Translate genotype to standardized CPIC phenotype.
        """
        allele_1, allele_2 = alleles
        
        # Check if gene has a registered phenotype function
        if gene not in GENE_PHENOTYPE_FUNCTIONS:
            logger.warning(
                f"Gene {gene} not found in phenotype function registry"
            )
            return "Unknown Phenotype"
        
        phenotype_function = GENE_PHENOTYPE_FUNCTIONS[gene]
        
        # Metabolic enzymes use Activity Score
        if gene in METABOLIC_ENZYMES:
            if score is None:
                logger.error(
                    f"Activity Score required for {gene} but not provided"
                )
                return "Unknown Phenotype"
            
            phenotype = phenotype_function(score)
            logger.info(
                f"Translated {gene} Activity Score {score} → '{phenotype}'"
            )
            return phenotype
        
        # Transporters use diplotype mapping
        else:
            phenotype = phenotype_function(allele_1, allele_2)
            logger.info(
                f"Translated {gene} diplotype {allele_1}/{allele_2} → '{phenotype}'"
            )
            return phenotype
    
    async def get_clinical_profile(
        self,
        patient_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate complete clinical phenotype profile for a patient.
        """
        logger.info(f"Generating clinical profile for patient_id='{patient_id}'")
        
        try:
            # Retrieve genotypes from Azure PostgreSQL
            genotypes = await self.genomic_service.get_patient_genotypes(patient_id)
            
            logger.info(
                f"Retrieved genotypes for {len(genotypes)} genes from database"
            )
            
            # Build phenotype profiles for each gene
            clinical_profile: Dict[str, Dict[str, Any]] = {}
            
            for gene, alleles in genotypes.items():
                # Handle missing genomic data
                if alleles == "Missing":
                    profile = PhenotypeProfile(
                        gene=gene,
                        allele_1=None,
                        allele_2=None,
                        activity_score=None,
                        phenotype="Data Missing/Unknown",
                        data_available=False,
                    )
                    
                    clinical_profile[gene] = profile.to_dict()
                    
                    logger.warning(
                        f"Gene {gene} has no data for patient_id='{patient_id}' - "
                        f"set to 'Data Missing/Unknown' for Grey status"
                    )
                    continue
                
                # Add instance check for alleles tuple to prevent type errors
                if not isinstance(alleles, tuple):
                    continue 

                # Alleles are present - calculate phenotype
                allele_1, allele_2 = alleles
                
                # Calculate Activity Score (for CYP genes only)
                activity_score = self.calculate_score(gene, alleles)
                
                # Translate to phenotype
                phenotype = self.translate_phenotype(gene, alleles, activity_score)
                
                # Create structured profile
                profile = PhenotypeProfile(
                    gene=gene,
                    allele_1=allele_1,
                    allele_2=allele_2,
                    activity_score=activity_score,
                    phenotype=phenotype,
                    data_available=True,
                )
                
                clinical_profile[gene] = profile.to_dict()
                
                logger.info(
                    f"Generated phenotype for {gene}: "
                    f"{allele_1}/{allele_2} → '{phenotype}'"
                )
            
            logger.info(
                f"Successfully generated clinical profile for patient_id='{patient_id}' "
                f"with {len(clinical_profile)} genes"
            )
            
            return clinical_profile
        
        except GenomicDataNotFoundError:
            # Return 'Data Missing/Unknown' for all genes if patient has no genomic data
            logger.warning(
                f"No genomic data found for patient_id='{patient_id}' - "
                f"returning missing status for all genes"
            )
            
            clinical_profile = {}
            for gene in ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]:
                profile = PhenotypeProfile(
                    gene=gene,
                    allele_1=None,
                    allele_2=None,
                    activity_score=None,
                    phenotype="Data Missing/Unknown",
                    data_available=False,
                )
                clinical_profile[gene] = profile.to_dict()
            
            return clinical_profile
        
        except GenomicConnectionError:
            # Re-raise database connection errors for graceful failure
            raise
        
        except Exception as e:
            logger.error(
                f"Unexpected error generating clinical profile for "
                f"patient_id='{patient_id}': {e}",
                exc_info=True
            )
            raise PhenotypeCalculationError(
                message="Failed to generate clinical phenotype profile",
                details=str(e)
            )


# Factory Function
def create_phenotype_service() -> PhenotypeService:
    """
    Factory function to create a PhenotypeService instance.
    """
    return PhenotypeService()
