"""
Unit tests for app/services/recommendation_service.py — private helper methods.
"""

import pytest
from unittest.mock import MagicMock
from app.models.recommendation import DrugRecommendation


@pytest.mark.unit
class TestRecommendationServiceHelpers:
    """
    Pure-unit tests for non-async private methods.
    """
    def _service(self):
        from app.services.recommendation_service import RecommendationService
        mock_fhir = MagicMock()
        return RecommendationService(fhir_service=mock_fhir)

    # _determine_alert_color
    @pytest.mark.parametrize("rec,classification,phenotype,expected", [
        # RED keywords + Strong classification -> RED
        ("Avoid codeine use.", "Strong",   "Poor Metabolizer",    "RED"),
        # RED keyword + poor phenotype (overrides Moderate to RED)
        ("Avoid this drug.",   "Moderate", "Poor Metabolizer",    "RED"),
        # RED keyword + Moderate + normal phenotype -> YELLOW
        ("Avoid if possible.", "Moderate", "Normal Metabolizer",  "YELLOW"),
        # Contraindicated keyword + Strong -> RED
        ("Contraindicated.",   "Strong",   "Normal Metabolizer",  "RED"),
        # Dose reduction + Poor phenotype -> RED (elevated risk)
        ("Dose reduction recommended.", "Moderate", "Poor Metabolizer",  "RED"),
        # Dose reduction + Normal phenotype -> YELLOW
        ("Dose reduction by 50%.",      "Moderate", "Normal Metabolizer","YELLOW"),
        # Monitor + Normal -> YELLOW
        ("Monitor closely.",            "Moderate", "Normal Metabolizer","YELLOW"),
        # Caution + any -> YELLOW
        ("Use with caution.",           "Optional", "Intermediate Metabolizer", "YELLOW"),
        # Standard dosing -> GREEN
        ("Use standard dosing.",        "Strong",   "Normal Metabolizer",  "GREEN"),
        # label-recommended -> GREEN
        ("Use label-recommended dose.", "Standard", "Normal Function",     "GREEN"),
        # No change -> GREEN
        ("No change to therapy needed.","Strong",   "Normal Metabolizer",  "GREEN"),
        # Adjustment + Poor -> RED
        ("Dose adjustment required.",   "Moderate", "Poor Metabolizer",    "RED"),
        # Adjustment + Normal -> YELLOW
        ("Dose adjustment required.",   "Moderate", "Normal Metabolizer",  "YELLOW"),
    ])
    def test_determine_alert_color(self, rec, classification, phenotype, expected):
        svc = self._service()
        color = svc._determine_alert_color(rec, classification, phenotype)
        assert color == expected

    # _normalize_med_name
    @pytest.mark.parametrize("raw,expected", [
        ("Codeine",                             "Codeine"),
        ("acebutolol (acebutolol 200 mg oral capsule)", "acebutolol"),
        ("metoprolol 50 mg oral tablet",        "metoprolol"),
        ("Simvastatin 20mg",                    "Simvastatin"),
        ("clopidogrel 75 mg oral tablet",       "clopidogrel"),
    ])
    def test_normalize_med_name(self, raw, expected):
        svc = self._service()
        result = svc._normalize_med_name(raw)
        assert result.lower().startswith(expected.lower())

    # _medication_matches
    @pytest.mark.parametrize("drug_name,active_meds,expected", [
        # Exact match
        ("codeine",     ["codeine", "aspirin"],    True),
        # First-word match with long base word
        ("codeine",     ["codeine sulfate"],        True),
        # Drug base word matches first word of active med
        ("metoprolol",  ["metoprolol tartrate"],   True),
        # substring must NOT match (escitalopram different from citalopram)
        ("citalopram",  ["escitalopram"],           False),
        # Not in list at all
        ("warfarin",    ["codeine", "aspirin"],     False),
        # Short base word (<= 4 chars) should not use first-word match
        ("abcd",        ["abcde"],                  False),
    ])
    def test_medication_matches(self, drug_name, active_meds, expected):
        svc = self._service()
        assert svc._medication_matches(drug_name, active_meds) == expected

    # _categorize_alerts
    def test_categorize_alerts_grey_for_missing_genomic_data(self):
        """
        A gene with data_available=False must produce a GREY DrugRecommendation.
        """
        svc = self._service()
        phenotype_profile = {
            "CYP2D6": {
                "data_available": False,
                "phenotype": "Data Missing/Unknown",
            }
        }
        response = svc._categorize_alerts(
            recommendations=[],
            patient_id="DEMO007",
            phenotype_profile=phenotype_profile,
            active_medication_names=["Codeine"],
            gene_substrates={"CYP2D6": ["Codeine", "Tramadol"]},
        )
        assert len(response.grey_alerts) >= 1
        grey = response.grey_alerts[0]
        assert grey.alert_color == "GREY"
        assert grey.gene_symbol == "CYP2D6"
        assert grey.phenotype   == "Data Missing/Unknown"
        assert "CYP2D6" in grey.clinical_action

    def test_categorize_alerts_grey_no_cpic_guidelines(self):
        """
        Gene has genomic data but no CPIC Level A/B recommendations matched
        current meds -> a GREY 'No CPIC Guidelines' card must be added.
        """
        svc = self._service()
        phenotype_profile = {
            "ABCB1": {
                "data_available": True,
                "phenotype": "Reduced Transport Function",
            }
        }
        response = svc._categorize_alerts(
            recommendations=[],
            patient_id="DEMO004",
            phenotype_profile=phenotype_profile,
            active_medication_names=["Digoxin"],
            gene_substrates={"ABCB1": []},
        )
        grey_genes = [r.gene_symbol for r in response.grey_alerts]
        assert "ABCB1" in grey_genes

    def test_categorize_alerts_red_yellow_green_buckets(self):
        """
        Existing RED/YELLOW/GREEN recs flow into the correct buckets.
        """
        svc = self._service()

        recs = [
            DrugRecommendation(
                drug_name="Codeine", gene_symbol="CYP2D6",
                phenotype="Poor Metabolizer", alert_color="RED",
                clinical_action="Avoid.", guideline_url="http://cpic",
            ),
            DrugRecommendation(
                drug_name="Metoprolol", gene_symbol="CYP2D6",
                phenotype="Poor Metabolizer", alert_color="YELLOW",
                clinical_action="Reduce dose.", guideline_url="http://cpic",
            ),
            DrugRecommendation(
                drug_name="Clopidogrel", gene_symbol="CYP2C19",
                phenotype="Normal Metabolizer", alert_color="GREEN",
                clinical_action="Standard dose.", guideline_url="http://cpic",
            ),
        ]
        phenotype_profile = {
            "CYP2D6":  {"data_available": True, "phenotype": "Poor Metabolizer"},
            "CYP2C19": {"data_available": True, "phenotype": "Normal Metabolizer"},
        }
        response = svc._categorize_alerts(
            recommendations=recs,
            patient_id="DEMO001",
            phenotype_profile=phenotype_profile,
            active_medication_names=["codeine", "metoprolol", "clopidogrel"],
        )
        assert len(response.red_alerts)    == 1
        assert len(response.yellow_alerts) == 1
        assert len(response.green_alerts)  == 1

    def test_categorize_alerts_affected_medications_populated(self):
        """
        GREY card's affected_medications must list the patient's matching drugs.
        """
        svc = self._service()
        phenotype_profile = {
            "CYP2D6": {"data_available": False, "phenotype": "Data Missing/Unknown"}
        }
        response = svc._categorize_alerts(
            recommendations=[],
            patient_id="DEMO007",
            phenotype_profile=phenotype_profile,
            active_medication_names=["codeine", "tramadol", "aspirin"],
            gene_substrates={"CYP2D6": ["Codeine", "Tramadol"]},
        )
        grey = response.grey_alerts[0]
        assert grey.affected_medications is not None
        affected_lower = [m.lower() for m in grey.affected_medications]
        assert "codeine"  in affected_lower
        assert "tramadol" in affected_lower
        assert "aspirin"  not in affected_lower
