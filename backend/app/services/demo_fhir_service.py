"""
Demo FHIR Service - Provides synthetic medication data for demo patients
This bypasses Cerner FHIR API for demonstration purposes with comprehensive medication profiles
"""
from typing import List, Optional
from ..models.schemas import FHIRBundle, FHIRBundleEntry, FHIRMedicationRequest, FHIRCodeableConcept, FHIRReference


class DemoFHIRService:
    """
    Provides synthetic medication data for demo patients with comprehensive drug profiles.
    """
    # Comprehensive medication profiles for each demo patient
    DEMO_MEDICATIONS = {
        "DEMO001": [
            # High-Risk Polypharmacy Patient (8 medications)
            "Codeine",          # CYP2D6 - RED alert: Poor metabolizer
            "Clopidogrel",      # CYP2C19 - RED alert: Reduced efficacy
            "Simvastatin",      # SLCO1B1 - RED alert: High myopathy risk
            "Amitriptyline",    # CYP2D6 + CYP2C19 - RED alerts
            "Omeprazole",       # CYP2C19 - YELLOW alert
            "Metoprolol",       # CYP2D6 - YELLOW alert
            "Tramadol",         # CYP2D6 - RED alert
            "Venlafaxine",      # CYP2D6 - YELLOW alert
        ],
        "DEMO002": [
            # Ideal Candidate Profile (6 medications - all GREEN)
            "Codeine",          # GREEN - Normal metabolizer
            "Clopidogrel",      # GREEN - Normal metabolizer
            "Atorvastatin",     # GREEN - Normal function
            "Citalopram",       # GREEN - Normal metabolizer
            "Tramadol",         # GREEN - Normal metabolizer
            "Omeprazole",       # GREEN - Normal metabolizer
        ],
        "DEMO003": [
            # Ultrarapid Metabolizer (5 medications - toxicity risk)
            "Codeine",          # RED: Ultrarapid → high morphine levels
            "Tramadol",         # RED: Ultrarapid → avoid
            "Citalopram",       # YELLOW: Rapid CYP2C19
            "Omeprazole",       # YELLOW: Rapid → reduced efficacy
            "Voriconazole",     # YELLOW: Rapid → dose adjustment
        ],
        "DEMO004": [
            # Mixed Phenotype Profile (9 medications - all four alert types)
            # RED (Poor CYP2D6 Poor Metabolizer - dose reduction/avoid)
            "Codeine",          # RED: Poor CYP2D6 → avoid (Strong)
            "Tramadol",         # RED: Poor CYP2D6 → avoid (Strong)
            "Metoprolol",       # RED: Poor CYP2D6 → reduce dose 50-75% (Poor elevates to RED)
            "Aripiprazole",     # RED: Poor CYP2D6 → reduce dose 50% (Poor elevates to RED)
            # YELLOW (Decreased SLCO1B1 Function - dose adjustment)
            "Simvastatin",      # YELLOW: Decreased SLCO1B1 → lower dose/alternative (Moderate)
            "Atorvastatin",     # YELLOW: Decreased SLCO1B1 → monitor closely (Moderate)
            # GREEN (Normal CYP2C19 Metabolizer - standard dosing)
            "Clopidogrel",      # GREEN: Normal CYP2C19 → label dose
            "Citalopram",       # GREEN: Normal CYP2C19 → standard dose
            "Omeprazole",       # GREEN: Normal CYP2C19 → standard dose
            # GREY: ABCB1 has data but no CPIC Level A/B guidelines → "No applicable guidelines"
        ],
        "DEMO005": [
            # Cardiovascular Polypharmacy (6 medications - cardiac focus)
            "Clopidogrel",      # YELLOW: Intermediate CYP2C19
            "Metoprolol",       # YELLOW: Intermediate CYP2D6
            "Atorvastatin",     # YELLOW: Decreased SLCO1B1
            "Simvastatin",      # RED: Decreased SLCO1B1 → avoid
            "Carvedilol",       # YELLOW: Intermediate CYP2D6
            "Propranolol",      # YELLOW: Intermediate CYP2D6
        ],
        "DEMO006": [
            # Psychiatric Polypharmacy (10 medications - all four alert types)
            # RED (Poor CYP2D6 - avoid or dose-reduce; Poor Metabolizer elevates to RED)
            "Amitriptyline",    # RED: Poor CYP2D6 → alternative/50% reduction (Strong)
            "Atomoxetine",      # RED: Poor CYP2D6 → reduce to 50% target dose (Strong)
            "Venlafaxine",      # RED: Poor CYP2D6 → 50% reduction (Poor elevates to RED)
            "Paroxetine",       # RED: Poor CYP2D6 → alternative/50% reduction (Poor elevates to RED)
            "Aripiprazole",     # RED: Poor CYP2D6 → reduce dose 50% (Poor elevates to RED)
            "Risperidone",      # RED: Poor CYP2D6 → 50% reduction (Poor elevates to RED)
            # YELLOW (Intermediate CYP2C19 - dose adjustment)
            "Citalopram",       # YELLOW: Intermediate CYP2C19 → 25-50% reduction (Moderate)
            "Clopidogrel",      # YELLOW: Intermediate CYP2C19 → alternative recommended (Moderate)
            # GREEN (Normal SLCO1B1 Function - standard dosing)
            "Simvastatin",      # GREEN: Normal SLCO1B1 → label-recommended dosage
            "Atorvastatin",     # GREEN: Normal SLCO1B1 → label-recommended dosage
            # GREY: ABCB1 has data but no CPIC Level A/B guidelines → "No applicable guidelines"
        ],
        "DEMO007": [
            # No Genomic Data Patient (5 medications)
            # ALL genes are missing from the database → all GREY cards
            # "Action Required: Order genomic testing" for CYP2D6, CYP2C19, SLCO1B1, ABCB1
            "Codeine",          # GREY: No CYP2D6 data → cannot provide guidance
            "Clopidogrel",      # GREY: No CYP2C19 data → cannot provide guidance
            "Simvastatin",      # GREY: No SLCO1B1 data → cannot provide guidance
            "Amitriptyline",    # GREY: No CYP2D6/CYP2C19 data → cannot provide guidance
            "Omeprazole",       # GREY: No CYP2C19 data → cannot provide guidance
        ],
    }
    
    @staticmethod
    def is_demo_patient(patient_id: str) -> bool:
        """
        Check if patient ID is a demo patient.
        """
        return patient_id.startswith("DEMO")
    
    @staticmethod
    def get_active_medications(patient_id: str) -> Optional[FHIRBundle]:
        """
        Get synthetic medications for demo patients.
        """
        if not DemoFHIRService.is_demo_patient(patient_id):
            return None
        
        medications = DemoFHIRService.DEMO_MEDICATIONS.get(patient_id, [])
        
        if not medications:
            # Return empty bundle for unknown demo patient
            return FHIRBundle(
                resourceType="Bundle",
                type="searchset",
                total=0,
                entry=[]
            )
        
        # Create FHIR bundle with synthetic medication entries
        entries: List[FHIRBundleEntry] = []
        for medication_name in medications:
            med_request = FHIRMedicationRequest(
                resourceType="MedicationRequest",
                id=f"demo-{patient_id}-{medication_name}",
                status="active",
                intent="order",
                medicationCodeableConcept=FHIRCodeableConcept(
                    coding=[{
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": "demo-code",
                        "display": medication_name
                    }],
                    text=medication_name
                ),
                subject=FHIRReference(
                    reference=f"Patient/{patient_id}",
                    display=f"Demo Patient {patient_id}"
                ),
                authoredOn=None
            )
            
            entries.append(FHIRBundleEntry(
                fullUrl=f"https://demo.pharmaco-navigator.local/MedicationRequest/{med_request.id}",
                resource=med_request.model_dump()
            ))
        
        return FHIRBundle(
            resourceType="Bundle",
            type="searchset",
            total=len(medications),
            entry=entries
        )
    
    @staticmethod
    def get_demo_patient_info(patient_id: str) -> dict:
        """
        Get information about demo patient.
        """
        demo_info = {
            "DEMO001": {
                "name": "High-Risk Polypharmacy Patient",
                "description": "Elderly patient on 8 medications with multiple drug-gene interactions",
                "genotype_summary": "Poor CYP2D6, Poor CYP2C19, Decreased SLCO1B1",
                "expected_alerts": "Multiple RED/YELLOW alerts (high-risk profile)",
                "medication_count": 8,
            },
            "DEMO002": {
                "name": "Ideal Candidate Patient",
                "description": "Normal metabolizer across all genes (best-case scenario)",
                "genotype_summary": "Normal CYP2D6, Normal CYP2C19, Normal SLCO1B1",
                "expected_alerts": "All GREEN alerts (standard dosing)",
                "medication_count": 6,
            },
            "DEMO003": {
                "name": "Ultrarapid Metabolizer",
                "description": "Ultrarapid CYP2D6, Rapid CYP2C19 (opposite of poor metabolizer)",
                "genotype_summary": "Ultrarapid CYP2D6, Rapid CYP2C19, Normal SLCO1B1",
                "expected_alerts": "RED/YELLOW for toxicity risk",
                "medication_count": 5,
            },
            "DEMO004": {
                "name": "Mixed Phenotype Patient",
                "description": "Mix of risk factors across different genes — demonstrates all four alert types (RED/YELLOW/GREEN/GREY)",
                "genotype_summary": "Poor CYP2D6, Normal CYP2C19, Decreased SLCO1B1, ABCB1 pending testing",
                "expected_alerts": "RED (CYP2D6 drugs), YELLOW (statins), GREEN (CYP2C19 drugs), GREY (order ABCB1 testing)",
                "medication_count": 9,
            },
            "DEMO005": {
                "name": "Cardiovascular Polypharmacy",
                "description": "Cardiac patient on multiple cardiovascular drugs",
                "genotype_summary": "Intermediate CYP2D6, Intermediate CYP2C19, Decreased SLCO1B1",
                "expected_alerts": "YELLOW alerts for multiple cardiac medications",
                "medication_count": 6,
            },
            "DEMO006": {
                "name": "Psychiatric Polypharmacy",
                "description": "Mental health patient on multiple psychotropics — demonstrates all four alert types (RED/YELLOW/GREEN/GREY)",
                "genotype_summary": "Poor CYP2D6, Intermediate CYP2C19, Normal SLCO1B1",
                "expected_alerts": "RED (CYP2D6 psych drugs), YELLOW (CYP2C19 dose-adjust), GREEN (statins), GREY (ABCB1 no guidelines)",
                "medication_count": 10,
            },
            "DEMO007": {
                "name": "No Genomic Data Patient",
                "description": "Patient with no pharmacogenomic testing on file — all genes missing, demonstrates Action Required grey cards",
                "genotype_summary": "No genomic data available — testing not ordered",
                "expected_alerts": "All GREY alerts (Action Required: Order genomic testing for all genes)",
                "medication_count": 5,
            },
        }
        
        return demo_info.get(patient_id, {
            "name": "Unknown Demo Patient",
            "description": "No information available",
            "genotype_summary": "Unknown",
            "expected_alerts": "Unknown",
            "medication_count": 0,
        })
