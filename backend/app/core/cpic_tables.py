"""
CPIC Pharmacogenomic Knowledge Base.
Mapping tables for phenotype translation following CPIC standards.
"""

from typing import Dict, Tuple, Callable


# CYP2D6 - Metabolic Enzyme (Activity Score Method)
# Star-allele to Activity Score mapping based on CPIC CYP2D6 allele functionality table
CYP2D6_ALLELE_SCORES: Dict[str, float] = {
    "*1": 1.0,   # Normal function
    "*2": 1.0,   # Normal function
    "*4": 0.0,   # No function
    "*5": 0.0,   # No function (gene deletion)
    "*10": 0.25, # Decreased function
    "*17": 0.5,  # Decreased function
    "*41": 0.5,  # Decreased function
}
# Default score for unknown alleles
CYP2D6_DEFAULT_SCORE = 1.0  # Assume normal function if unknown


def get_cyp2d6_phenotype(activity_score: float) -> str:
    """
    Map CYP2D6 Activity Score to standardized CPIC phenotype.
    """
    if activity_score == 0:
        return "Poor Metabolizer"
    elif 0 < activity_score < 1.25:
        return "Intermediate Metabolizer"
    elif 1.25 <= activity_score <= 2.25:
        return "Normal Metabolizer"
    else:  # activity_score > 2.25
        return "Ultrarapid Metabolizer"


# CYP2C19 - Metabolic Enzyme (Activity Score Method)
# Star-allele to Activity Score mapping based on CPIC CYP2C19 allele functionality table
CYP2C19_ALLELE_SCORES: Dict[str, float] = {
    "*1": 1.0,   # Normal function
    "*2": 0.0,   # No function
    "*3": 0.0,   # No function
    "*17": 1.0,  # Increased function 
}
# Default score for unknown alleles
CYP2C19_DEFAULT_SCORE = 1.0  # Assume normal function if unknown


def get_cyp2c19_phenotype(activity_score: float) -> str:
    """
    Map CYP2C19 Activity Score to standardized CPIC phenotype.
    """
    if activity_score == 0:
        return "Poor Metabolizer"
    elif 1.0 <= activity_score <= 1.5:
        return "Intermediate Metabolizer"
    elif activity_score == 2.0:
        return "Normal Metabolizer"
    else:  # activity_score > 2.0
        return "Ultrarapid Metabolizer"


# SLCO1B1 - Transmembrane Transporter (Functional Mapping)
# Diplotype to Functional Status mapping based on CPIC SLCO1B1 guidelines for simvastatin
SLCO1B1_DIPLOTYPE_PHENOTYPES: Dict[Tuple[str, str], str] = {
    # Normal Function diplotypes
    # *1A is the reference haplotype (equivalent to *1, normal function)
    ("*1", "*1"): "Normal Function",
    ("*1A", "*1A"): "Normal Function",
    ("*1A", "*1"): "Normal Function",
    ("*1", "*1A"): "Normal Function",

    # Decreased Function diplotypes (one decreased function allele)
    ("*1", "*5"): "Decreased Function",
    ("*5", "*1"): "Decreased Function",
    ("*1A", "*5"): "Decreased Function",
    ("*5", "*1A"): "Decreased Function",
    ("*1", "*15"): "Decreased Function",
    ("*15", "*1"): "Decreased Function",
    ("*1A", "*15"): "Decreased Function",
    ("*15", "*1A"): "Decreased Function",

    # Poor Function diplotypes (two decreased function alleles)
    ("*5", "*5"): "Poor Function",
    ("*15", "*15"): "Poor Function",
    ("*5", "*15"): "Poor Function",
    ("*15", "*5"): "Poor Function",
}
# Default phenotype for unknown diplotypes
SLCO1B1_DEFAULT_PHENOTYPE = "Unknown Function"


def get_slco1b1_phenotype(allele_1: str, allele_2: str) -> str:
    """
    Map SLCO1B1 diplotype to standardized CPIC functional status.
    
    CPIC Functional Status Mapping:
        *1/*1                    → Normal Function
        *1/*5 or *1/*15          → Decreased Function
        *5/*5, *15/*15, *5/*15   → Poor Function
    """
    # Try forward order
    diplotype = (allele_1, allele_2)
    if diplotype in SLCO1B1_DIPLOTYPE_PHENOTYPES:
        return SLCO1B1_DIPLOTYPE_PHENOTYPES[diplotype]
    
    # Try reverse order
    diplotype_reverse = (allele_2, allele_1)
    if diplotype_reverse in SLCO1B1_DIPLOTYPE_PHENOTYPES:
        return SLCO1B1_DIPLOTYPE_PHENOTYPES[diplotype_reverse]
    
    # Unknown diplotype
    return SLCO1B1_DEFAULT_PHENOTYPE


# ABCB1 - Transmembrane Transporter (SNP-Based Genotype Mapping)
# rs1045642 (C3435T) genotype to Functional Status mapping based on nucleotide alleles (C/T)
ABCB1_GENOTYPE_PHENOTYPES: Dict[Tuple[str, str], str] = {
    # Normal transport function
    ("C", "C"): "Normal Transport Function",
    
    # Intermediate transport function (heterozygous)
    ("C", "T"): "Intermediate Transport Function",
    ("T", "C"): "Intermediate Transport Function",
    
    # Reduced transport function (homozygous variant)
    ("T", "T"): "Reduced Transport Function",
    
    # Star-allele notation equivalents
    ("*1", "*1"): "Normal Transport Function",
    ("*1", "*2"): "Intermediate Transport Function",
    ("*2", "*1"): "Intermediate Transport Function",
    ("*2", "*2"): "Reduced Transport Function",
}
# Default phenotype for unknown genotypes
ABCB1_DEFAULT_PHENOTYPE = "Unknown Transport Function"


def get_abcb1_phenotype(allele_1: str, allele_2: str) -> str:
    """
    Map ABCB1 genotype (rs1045642 variant) to standardized functional status.
    
    Functional Status Mapping:
        C/C or *1/*1 → Normal Transport Function
        C/T or *1/*2 → Intermediate Transport Function
        T/T or *2/*2 → Reduced Transport Function
    """
    def _normalize(allele: str) -> str:
        # SNP notation "1234X>Y" → take the character after ">"
        if ">" in allele:
            return allele.split(">")[-1].strip().upper()
        return allele.strip().upper()

    a1 = _normalize(allele_1)
    a2 = _normalize(allele_2)

    # Try forward order
    genotype = (a1, a2)
    if genotype in ABCB1_GENOTYPE_PHENOTYPES:
        return ABCB1_GENOTYPE_PHENOTYPES[genotype]
    
    # Try reverse order
    genotype_reverse = (a2, a1)
    if genotype_reverse in ABCB1_GENOTYPE_PHENOTYPES:
        return ABCB1_GENOTYPE_PHENOTYPES[genotype_reverse]
    
    # Unknown genotype
    return ABCB1_DEFAULT_PHENOTYPE


# Unified Gene Registry
# Map gene symbols to their allele score tables
GENE_ALLELE_SCORES: Dict[str, Dict[str, float]] = {
    "CYP2D6": CYP2D6_ALLELE_SCORES,
    "CYP2C19": CYP2C19_ALLELE_SCORES,
}

# Map gene symbols to their default scores
GENE_DEFAULT_SCORES: Dict[str, float] = {
    "CYP2D6": CYP2D6_DEFAULT_SCORE,
    "CYP2C19": CYP2C19_DEFAULT_SCORE,
}

# Map gene symbols to their phenotype translation functions
GENE_PHENOTYPE_FUNCTIONS: Dict[str, Callable] = {
    "CYP2D6": get_cyp2d6_phenotype,
    "CYP2C19": get_cyp2c19_phenotype,
    "SLCO1B1": get_slco1b1_phenotype,
    "ABCB1": get_abcb1_phenotype,
}

# Gene types for orchestration logic
METABOLIC_ENZYMES = ["CYP2D6", "CYP2C19"]
TRANSPORTERS = ["SLCO1B1", "ABCB1"]
