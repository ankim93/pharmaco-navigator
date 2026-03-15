"""
Unit tests for app/services/demo_fhir_service.py.
"""

import pytest


@pytest.mark.unit
class TestDemoFHIRService:

    @pytest.mark.parametrize("patient_id,expected", [
        ("DEMO001", True),
        ("DEMO007", True),
        ("12724067", False),
        ("real-patient", False),
        ("", False),
    ])
    def test_is_demo_patient(self, patient_id, expected):
        from app.services.demo_fhir_service import DemoFHIRService
        assert DemoFHIRService.is_demo_patient(patient_id) == expected

    def test_demo001_returns_8_medications(self):
        from app.services.demo_fhir_service import DemoFHIRService
        bundle = DemoFHIRService.get_active_medications("DEMO001")
        assert bundle is not None
        assert bundle.total == 8
        assert len(bundle.entry) == 8

    def test_demo002_returns_6_medications(self):
        from app.services.demo_fhir_service import DemoFHIRService
        bundle = DemoFHIRService.get_active_medications("DEMO002")
        assert bundle is not None
        assert bundle.total == 6

    def test_demo007_returns_5_medications(self):
        """DEMO007 is the no-genomic-data patient — still has valid medication list."""
        from app.services.demo_fhir_service import DemoFHIRService
        bundle = DemoFHIRService.get_active_medications("DEMO007")
        assert bundle is not None
        assert bundle.total == 5

    def test_non_demo_patient_returns_none(self):
        from app.services.demo_fhir_service import DemoFHIRService
        result = DemoFHIRService.get_active_medications("12724067")
        assert result is None

    def test_unknown_demo_id_returns_empty_bundle(self):
        from app.services.demo_fhir_service import DemoFHIRService
        bundle = DemoFHIRService.get_active_medications("DEMO999")
        assert bundle is not None
        assert bundle.total == 0
        assert bundle.entry == []

    def test_demo001_includes_codeine_in_entries(self):
        from app.services.demo_fhir_service import DemoFHIRService
        bundle = DemoFHIRService.get_active_medications("DEMO001")
        texts = [
            e.resource.get("medicationCodeableConcept", {}).get("text", "")
            for e in bundle.entry
        ]
        assert "Codeine" in texts

    def test_bundle_entries_have_fhir_structure(self):
        from app.services.demo_fhir_service import DemoFHIRService
        bundle = DemoFHIRService.get_active_medications("DEMO001")
        for entry in bundle.entry:
            resource = entry.resource
            assert resource.get("resourceType") == "MedicationRequest"
            assert resource.get("status") == "active"
