"""
Phase 2 Phenotype Translation Service for Pharmaco Navigator.

Two independent computational pathways:
  - Linear Additive Scoring (CYP2D6, CYP2C19): sums per-allele CPIC activity
    scores from gene-specific lookup tables; unmapped alleles fall back to
    wild-type (1.0) and emit a structured WARNING log.
  - Categorical Tuple Routing (SLCO1B1, ABCB1): maps sorted diplotype pairs
    directly to function profiles; bypasses numerical scaling / rounding errors.

Missing or null database fields map to 'Data Missing/Unknown' without raising.
"""

import logging
from typing import Any, Dict, Optional, Sequence, Tuple, Union

from app.models.genotype import Genotype
from app.services.genomic_service import (
    GenomicConnectionError,
    GenomicDataNotFoundError,
    GenomicService,
    create_genomic_service,
)

logger = logging.getLogger("pharmaco.navigator.phenotype")

# =========================================================================== #
# Phase 2 -- self-contained, gene-specific scoring tables                     #
# =========================================================================== #
#
# CYP2D6 and CYP2C19 use SEPARATE tables: the same star-allele number can
# have a different activity value in each gene (*17 is decreased-function 0.5
# in CYP2D6 but normal-function 1.0 in CYP2C19; *2 is 1.0 in CYP2D6 but
# loss-of-function 0.0 in CYP2C19).
#

_CYP2D6_SCORES: dict[str, float] = {
    "*1":  1.0,   # normal function   (spec: *1=1.0)
    "*2":  1.0,   # normal function
    "*3":  0.0,   # no function
    "*4":  0.0,   # no function       (spec: *4=0.0)
    "*5":  0.0,   # no function (gene deletion)
    "*6":  0.0,   # no function
    "*9":  0.5,   # decreased function
    "*10": 0.25,  # decreased function
    "*17": 0.5,   # decreased function (CYP2D6 *17 differs from CYP2C19 *17)
    "*29": 0.5,   # decreased function
    "*41": 0.5,   # decreased function
}

_CYP2C19_SCORES: dict[str, float] = {
    "*1":  1.0,   # normal function   (spec: *1=1.0)
    "*2":  0.0,   # no function       (spec: *4=0.0 analogue for CYP2C19)
    "*3":  0.0,   # no function
    "*17": 1.0,   # normal function   (spec: *17=1.0 -- applies to CYP2C19)
}

_GENE_SCORES: dict[str, dict[str, float]] = {
    "CYP2D6":  _CYP2D6_SCORES,
    "CYP2C19": _CYP2C19_SCORES,
}
_GENE_DEFAULT_SCORE: dict[str, float] = {
    "CYP2D6":  1.0,
    "CYP2C19": 1.0,
}

_METABOLIC_GENES = frozenset({"CYP2D6", "CYP2C19"})
_TRANSPORTER_GENES = frozenset({"SLCO1B1", "ABCB1"})

# Categorical diplotype -> function profiles.
# ALL keys must be pre-sorted via tuple(sorted([a1, a2])) -- Python lex sort
# means "*15" < "*5" (because "1" < "5"), so the correct key for (*5, *15) is
# ("*15", "*5"), not ("*5", "*15").
_CATEGORICAL_MAPS: dict[str, dict[tuple[str, str], str]] = {
    "SLCO1B1": {
        ("*1",  "*1"):  "Normal Function",
        ("*1",  "*5"):  "Decreased Function",    # sorted: *1 < *5
        ("*1",  "*15"): "Decreased Function",    # sorted: *1 < *15
        ("*1",  "*17"): "Decreased Function",
        ("*1",  "*45"): "Decreased Function",
        ("*5",  "*5"):  "Poor Function",         # spec example: (*5,*5) -> Poor Function
        ("*15", "*5"):  "Poor Function",         # sorted: *15 < *5 (lex)
        ("*15", "*15"): "Poor Function",
        ("*17", "*17"): "Poor Function",
        ("*45", "*45"): "Poor Function",
    },
    # ABCB1 uses both SNP-level (C/T) and star-allele notation.
    # Phenotype labels include "Transport Function" per the ABCB1 clinical convention.
    "ABCB1": {
        ("C",  "C"):  "Normal Transport Function",
        ("C",  "T"):  "Intermediate Transport Function",
        ("T",  "T"):  "Reduced Transport Function",
        ("*1", "*2"): "Intermediate Transport Function",
        ("*1", "*3"): "Intermediate Transport Function",
        ("*2", "*2"): "Reduced Transport Function",
        ("*2", "*3"): "Reduced Transport Function",
        ("*3", "*3"): "Reduced Transport Function",
    },
}


def _score_to_metabolizer(score: float) -> str:
    """
    Map a total CPIC activity score to the canonical metabolizer phenotype string.

    Boundary at 1.25 belongs to Normal (inclusive lower bound), not Intermediate.
    """
    if score == 0.0:
        return "Poor Metabolizer"
    if score < 1.25:        # strictly less-than: 1.25 opens the Normal range
        return "Intermediate Metabolizer"
    if score <= 2.25:
        return "Normal Metabolizer"
    return "Ultrarapid Metabolizer"


def _diplotype_key(a1: str, a2: str) -> tuple[str, str]:
    """Return the canonical sorted tuple used as a categorical map lookup key."""
    return tuple(sorted([a1, a2]))  # type: ignore[return-value]


# =========================================================================== #
# Exceptions                                                                   #
# =========================================================================== #

class PhenotypeServiceError(Exception):
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)


class PhenotypeCalculationError(PhenotypeServiceError):
    pass


# =========================================================================== #
# Profile container (backward-compatible with patient.py and existing tests)  #
# =========================================================================== #

class PhenotypeProfile:
    def __init__(
        self,
        gene: str,
        allele_1: Optional[str] = None,
        allele_2: Optional[str] = None,
        activity_score: Optional[float] = None,
        phenotype: str = "Data Missing/Unknown",
        data_available: bool = False,
    ) -> None:
        self.gene = gene
        self.allele_1 = allele_1
        self.allele_2 = allele_2
        self.activity_score = activity_score
        self.phenotype = phenotype
        self.data_available = data_available

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gene": self.gene,
            "allele_1": self.allele_1,
            "allele_2": self.allele_2,
            "activity_score": self.activity_score,
            "phenotype": self.phenotype,
            "data_available": self.data_available,
        }

    def __repr__(self) -> str:
        if self.data_available:
            return (
                f"PhenotypeProfile(gene='{self.gene}', "
                f"genotype={self.allele_1}/{self.allele_2}, "
                f"activity_score={self.activity_score}, "
                f"phenotype='{self.phenotype}')"
            )
        return (
            f"PhenotypeProfile(gene='{self.gene}', "
            f"phenotype='{self.phenotype}', data_available=False)"
        )


# =========================================================================== #
# Service                                                                      #
# =========================================================================== #

class PhenotypeService:
    """
    Phase 2 phenotype calculation service.

    Logging identifier: "pharmaco.navigator.phenotype"
    """

    def __init__(self, genomic_service: Optional[GenomicService] = None) -> None:
        self.genomic_service = genomic_service or create_genomic_service()
        logger.info("PhenotypeService (Phase 2) initialised")

    # ------------------------------------------------------------------ #
    # Phase 2 public API                                                   #
    # ------------------------------------------------------------------ #

    def calculate_phenotypes(
        self,
        genotypes: Sequence[Union[Genotype, Dict[str, Any]]],
    ) -> Dict[str, str]:
        """
        Return {gene_symbol: phenotype_string} for each supplied genotype.

        - Missing or null allele fields -> "Data Missing/Unknown" (no crash).
        - Unmapped alleles fall back to wild-type (score 1.0) with a WARNING log.
        - Out-of-scope genes fire a WARNING and are silently skipped.
        """
        result: Dict[str, str] = {}
        for g in genotypes:
            gene, a1, a2 = self._extract_allele_fields(g)
            if not gene:
                continue
            if a1 is None or a2 is None:
                result[gene] = "Data Missing/Unknown"
                continue
            if gene in _METABOLIC_GENES:
                result[gene] = self._linear_additive(gene, a1, a2)
            elif gene in _TRANSPORTER_GENES:
                result[gene] = self._categorical_tuple(gene, a1, a2)
            else:
                logger.warning(
                    "Gene '%s' is outside the scope panel {CYP2D6, CYP2C19, SLCO1B1, ABCB1} -- skipped",
                    gene,
                )
        return result

    # ------------------------------------------------------------------ #
    # Pathway implementations                                              #
    # ------------------------------------------------------------------ #

    def _linear_additive(self, gene: str, a1: str, a2: str) -> str:
        """CYP2D6 / CYP2C19: sum per-allele activity scores -> metabolizer class."""
        s1 = self._allele_score(gene, a1)
        s2 = self._allele_score(gene, a2)
        total = s1 + s2
        phenotype = _score_to_metabolizer(total)
        logger.debug("%s: %s(%.2f) + %s(%.2f) = %.2f -> %s", gene, a1, s1, a2, s2, total, phenotype)
        return phenotype

    def _categorical_tuple(self, gene: str, a1: str, a2: str) -> str:
        """SLCO1B1 / ABCB1: look up sorted diplotype pair in the function index."""
        key = _diplotype_key(a1, a2)
        phenotype = _CATEGORICAL_MAPS.get(gene, {}).get(key)
        if phenotype is None:
            logger.warning(
                "Unmapped diplotype (%s, %s) for %s -- falling back to wild-type default",
                a1, a2, gene,
            )
            return "Normal Function"
        logger.debug("%s: (%s, %s) -> %s", gene, a1, a2, phenotype)
        return phenotype

    def _allele_score(self, gene: str, allele: str) -> float:
        gene_table = _GENE_SCORES.get(gene, {})
        score = gene_table.get(allele)
        if score is None:
            default = _GENE_DEFAULT_SCORE.get(gene, 1.0)
            logger.warning(
                "Unmapped allele '%s' for %s -- falling back to wild-type score %.2f",
                allele, gene, default,
            )
            return default
        return score

    @staticmethod
    def _extract_allele_fields(
        g: Union[Genotype, Dict[str, Any]],
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if isinstance(g, dict):
            gene = g.get("gene_symbol") or g.get("gene") or ""
            a1 = g.get("allele_1") or g.get("allele1")
            a2 = g.get("allele_2") or g.get("allele2")
        else:
            gene = getattr(g, "gene_symbol", "") or getattr(g, "gene", "")
            a1 = getattr(g, "allele_1", None) or getattr(g, "allele1", None)
            a2 = getattr(g, "allele_2", None) or getattr(g, "allele2", None)
        return (gene or None), (a1 or None), (a2 or None)

    # ------------------------------------------------------------------ #
    # Backward-compatible scoring helpers (consumed by existing tests)    #
    # ------------------------------------------------------------------ #

    def calculate_score(
        self,
        gene: str,
        alleles: Tuple[str, str],
    ) -> Optional[float]:
        """Return the summed activity score for CYP genes, or None for transporters."""
        if gene in _TRANSPORTER_GENES:
            return None
        if gene not in _METABOLIC_GENES:
            logger.warning("calculate_score called for out-of-scope gene '%s'", gene)
            return None
        a1, a2 = alleles
        return self._allele_score(gene, a1) + self._allele_score(gene, a2)

    def translate_phenotype(
        self,
        gene: str,
        alleles: Tuple[str, str],
        score: Optional[float] = None,
    ) -> str:
        """Translate a (gene, alleles) pair to a phenotype string."""
        a1, a2 = alleles
        if gene in _METABOLIC_GENES:
            if score is None:
                score = self.calculate_score(gene, alleles) or 0.0
            return _score_to_metabolizer(score)
        if gene in _TRANSPORTER_GENES:
            return self._categorical_tuple(gene, a1, a2)
        logger.warning("translate_phenotype called for out-of-scope gene '%s'", gene)
        return "Unknown Phenotype"

    # ------------------------------------------------------------------ #
    # Async profile builder (Phase 1 backward compatibility)              #
    # ------------------------------------------------------------------ #

    async def get_clinical_profile(
        self,
        patient_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve genotypes via the genomic service and return a per-gene
        phenotype profile dict compatible with the recommendation layer.
        """
        logger.info("Building clinical profile for patient_id='%s'", patient_id)
        try:
            genotypes_raw = await self.genomic_service.get_patient_genotypes(patient_id)
            clinical_profile: Dict[str, Dict[str, Any]] = {}

            for gene, alleles in genotypes_raw.items():
                if alleles == "Missing":
                    clinical_profile[gene] = PhenotypeProfile(gene=gene, data_available=False).to_dict()
                    logger.warning(
                        "Gene %s has no data for patient '%s' -- Data Missing/Unknown",
                        gene, patient_id,
                    )
                    continue

                if not isinstance(alleles, tuple):
                    logger.error(
                        "Unexpected allele format for gene %s: %r -- treating as missing",
                        gene, alleles,
                    )
                    clinical_profile[gene] = PhenotypeProfile(gene=gene, data_available=False).to_dict()
                    continue

                a1, a2 = alleles
                score = self.calculate_score(gene, alleles)
                phenotype = self.translate_phenotype(gene, alleles, score)

                clinical_profile[gene] = PhenotypeProfile(
                    gene=gene,
                    allele_1=a1,
                    allele_2=a2,
                    activity_score=score,
                    phenotype=phenotype,
                    data_available=True,
                ).to_dict()

                logger.info("%s %s/%s -> %s", gene, a1, a2, phenotype)

            return clinical_profile

        except GenomicDataNotFoundError:
            logger.warning(
                "No genomic data for patient '%s' -- all genes set to Data Missing/Unknown",
                patient_id,
            )
            return {
                gene: PhenotypeProfile(gene=gene, data_available=False).to_dict()
                for gene in ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]
            }

        except GenomicConnectionError:
            raise

        except Exception as exc:
            logger.exception(
                "Unexpected error building clinical profile for patient '%s'", patient_id
            )
            raise PhenotypeCalculationError(
                message="Failed to generate clinical phenotype profile",
                details=str(exc),
            ) from exc


def create_phenotype_service() -> PhenotypeService:
    return PhenotypeService()
