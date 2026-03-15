"""
Unit tests for app/core/cpic_tables.py — every phenotype mapping.
"""

import pytest


@pytest.mark.unit
class TestCPICTables:

    # CYP2D6
    @pytest.mark.parametrize("score,expected", [
        (0.0,   "Poor Metabolizer"),
        (0.25,  "Intermediate Metabolizer"),
        (0.5,   "Intermediate Metabolizer"),
        (1.0,   "Intermediate Metabolizer"),
        (1.25,  "Normal Metabolizer"),
        (2.0,   "Normal Metabolizer"),
        (2.25,  "Normal Metabolizer"),
        (2.5,   "Ultrarapid Metabolizer"),
        (3.0,   "Ultrarapid Metabolizer"),
    ])
    def test_cyp2d6_phenotype_mapping(self, score, expected):
        from app.core.cpic_tables import get_cyp2d6_phenotype
        assert get_cyp2d6_phenotype(score) == expected


    # CYP2C19
    @pytest.mark.parametrize("score,expected", [
        (0.0,  "Poor Metabolizer"),
        (1.0,  "Intermediate Metabolizer"),
        (1.5,  "Intermediate Metabolizer"),
        (2.0,  "Normal Metabolizer"),
        (2.5,  "Ultrarapid Metabolizer"),
        (3.0,  "Ultrarapid Metabolizer"),
    ])
    def test_cyp2c19_phenotype_mapping(self, score, expected):
        from app.core.cpic_tables import get_cyp2c19_phenotype
        assert get_cyp2c19_phenotype(score) == expected


    # SLCO1B1 
    @pytest.mark.parametrize("a1,a2,expected", [
        ("*1",   "*1",   "Normal Function"),
        ("*1A",  "*1A",  "Normal Function"),
        ("*1A",  "*1",   "Normal Function"),
        ("*1",   "*1A",  "Normal Function"),
        ("*1",   "*5",   "Decreased Function"),
        ("*5",   "*1",   "Decreased Function"),
        ("*1A",  "*5",   "Decreased Function"),
        ("*1",   "*15",  "Decreased Function"),
        ("*15",  "*1A",  "Decreased Function"),
        ("*5",   "*5",   "Poor Function"),
        ("*15",  "*15",  "Poor Function"),
        ("*5",   "*15",  "Poor Function"),
        ("*15",  "*5",   "Poor Function"),
        ("*99",  "*99",  "Unknown Function"),
    ])
    def test_slco1b1_phenotype_mapping(self, a1, a2, expected):
        from app.core.cpic_tables import get_slco1b1_phenotype
        assert get_slco1b1_phenotype(a1, a2) == expected


    # ABCB1
    @pytest.mark.parametrize("a1,a2,expected", [
        ("C",  "C",  "Normal Transport Function"),
        ("C",  "T",  "Intermediate Transport Function"),
        ("T",  "C",  "Intermediate Transport Function"),
        ("T",  "T",  "Reduced Transport Function"),
        ("*1", "*1", "Normal Transport Function"),
        ("*1", "*2", "Intermediate Transport Function"),
        ("*2", "*1", "Intermediate Transport Function"),
        ("*2", "*2", "Reduced Transport Function"),
        ("1236C>C", "1236C>C", "Normal Transport Function"),
        ("1236C>C", "3435C>T", "Intermediate Transport Function"),
        ("3435C>T", "3435C>T", "Reduced Transport Function"),
        ("UNKNOWN", "UNKNOWN", "Unknown Transport Function"),
    ])
    def test_abcb1_phenotype_mapping(self, a1, a2, expected):
        from app.core.cpic_tables import get_abcb1_phenotype
        assert get_abcb1_phenotype(a1, a2) == expected

    def test_gene_registries_structure(self):
        from app.core.cpic_tables import (
            GENE_ALLELE_SCORES,
            GENE_DEFAULT_SCORES,
            GENE_PHENOTYPE_FUNCTIONS,
        )
        assert "CYP2D6" in GENE_ALLELE_SCORES
        assert "CYP2C19" in GENE_ALLELE_SCORES
        assert "SLCO1B1" not in GENE_ALLELE_SCORES
        assert "CYP2D6" in GENE_DEFAULT_SCORES
        assert all(g in GENE_PHENOTYPE_FUNCTIONS for g in ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"])
