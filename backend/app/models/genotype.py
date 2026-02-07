"""
SQLModel schema for the genotypes table in Azure PostgreSQL.
Maps to the genotypes table containing patient star-allele data for pharmacogenomic screening.
"""

from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import String


class Genotype(SQLModel, table=True):
    """
    SQLModel representing the genotypes table in Azure PostgreSQL.
    """
    
    __tablename__: str = "genotypes"  # type: ignore[assignment]
    
    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Auto-incrementing primary key"
    )
    
    patient_id: str = Field(
        ...,
        max_length=255,
        index=True,
        description="Patient identifier from FHIR context (e.g., '12724067')"
    )
    
    gene_symbol: str = Field(
        ...,
        max_length=50,
        index=True,
        description="Gene symbol (e.g., 'CYP2D6', 'SLCO1B1')"
    )
    
    allele_1: str = Field(
        ...,
        max_length=50,
        description="First allele designation (e.g., '*1', '*2', '*5')"
    )
    
    allele_2: str = Field(
        ...,
        max_length=50,
        description="Second allele designation (e.g., '*1', '*4', '*17')"
    )
    
    class Config:
        """
        Pydantic configuration for SQLModel.
        """
        # Enable ORM mode for SQLAlchemy compatibility
        from_attributes = True
        
        # JSON schema example for API documentation
        json_schema_extra = {
            "example": {
                "id": 1,
                "patient_id": "12724067",
                "gene_symbol": "CYP2D6",
                "allele_1": "*1",
                "allele_2": "*4"
            }
        }
    
    def __repr__(self) -> str:
        """
        String representation for debugging.
        """
        return (
            f"Genotype(id={self.id}, patient_id='{self.patient_id}', "
            f"gene_symbol='{self.gene_symbol}', allele_1='{self.allele_1}', "
            f"allele_2='{self.allele_2}')"
        )
    
    @property
    def genotype_pair(self) -> tuple[str, str]:
        """
        Return allele pair as tuple for phenotype translation.
        """
        return (self.allele_1, self.allele_2)
