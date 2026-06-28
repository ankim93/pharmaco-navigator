"""
ORM model for the ``genotypes`` table.

Each row represents one diplotype observation for a single gene/patient pair.
The composite (patient_id, gene_symbol) pair is unique — concurrent upserts
should use ON CONFLICT (patient_id, gene_symbol) DO UPDATE rather than a
blind INSERT to avoid violating the constraint.
"""

from datetime import datetime
from typing import Optional
from datetime import datetime
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Genotype(SQLModel, table=True):
    __tablename__ = "genotypes"  # type: ignore[assignment]

    __table_args__ = (
        # One genotype row per patient per gene — enforced at the database level.
        UniqueConstraint("patient_id", "gene_symbol", name="uq_genotype_patient_gene"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # Indexed individually to support single-column lookups (patient dashboard,
    # gene-level analytics sweeps) without requiring a full table scan.
    patient_id: str = Field(index=True, max_length=255, nullable=False)
    gene_symbol: str = Field(index=True, max_length=50, nullable=False)

    # Star-allele notation per CPIC convention, e.g. "*1", "*4", "*17".
    allele_1: str = Field(max_length=50, nullable=False)
    allele_2: str = Field(max_length=50, nullable=False)

    # Audit timestamp set by insert_demo_patients.sql and live upsert paths.
    created_at: Optional[datetime] = Field(default=None)

    @property
    def diplotype_key(self) -> tuple[str, str]:
        """Canonical (sorted) allele pair used by PhenotypeService lookups."""
        return tuple(sorted([self.allele_1, self.allele_2]))  # type: ignore[return-value]

    def __repr__(self) -> str:
        return (
            f"Genotype(id={self.id}, patient_id='{self.patient_id}', "
            f"gene='{self.gene_symbol}', diplotype='{self.allele_1}/{self.allele_2}')"
        )
