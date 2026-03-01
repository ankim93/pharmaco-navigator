"""
Recommendation Service for Clinical Decision Support.
Orchestrates phenotype translation and CPIC guideline screening to generate Traffic Light dashboard alerts for drug-gene interactions.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any
from app.services.phenotype_service import (
    PhenotypeService,
    create_phenotype_service,
    PhenotypeCalculationError,
)
from app.services.cpic_service import (
    CPICService,
    create_cpic_service,
    CPICRecommendation,
    CPICConnectionError,
    CPICAPIError,
    CPICDataNotFoundError,
)
from app.services.genomic_service import GenomicConnectionError
from app.services.fhir_service import (
    FHIRService,
    FHIRConnectionError,
    FHIRAuthenticationError,
)
from app.services.demo_fhir_service import DemoFHIRService
from app.models.schemas import FHIRBundle
from app.models.recommendation import (
    DrugRecommendation,
    ClinicalAlertResponse,
    GenomicProfileSummary,
    AlertColor,
)
from app.core.fallback_guidelines import (
    get_fallback_recommendations,
    is_fallback_available,
)


# Configure logging
logger = logging.getLogger(__name__)


# Custom Exceptions (Graceful Failure)
class RecommendationServiceError(Exception):
    """
    Base exception for recommendation service errors.
    """
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


# RecommendationService Class
class RecommendationService:
    """
    Orchestration service for generating clinical decision support alerts.
    """
    def __init__(
        self,
        phenotype_service: Optional[PhenotypeService] = None,
        cpic_service: Optional[CPICService] = None,
        fhir_service: Optional[FHIRService] = None
    ):
        """
        Initialize RecommendationService for production mode.
        """
        self.phenotype_service = phenotype_service or create_phenotype_service()
        self.cpic_service = cpic_service or create_cpic_service()
        self.fhir_service = fhir_service
        # Lazy-loaded per-gene substrate cache populated from CPIC /pair API
        self._gene_substrates_cache: Dict[str, List[str]] = {}
        logger.info("RecommendationService initialized in production mode")
    
    async def generate_clinical_alerts(
        self,
        patient_id: str
    ) -> ClinicalAlertResponse:
        """
        Generate Traffic Light clinical alerts for a patient.
        """
        logger.info(f"Generating clinical alerts for patient_id='{patient_id}'")
        
        try:
            # Check if this is a demo patient - use synthetic medications
            if DemoFHIRService.is_demo_patient(patient_id):
                logger.info(f"Using demo FHIR service for demo patient {patient_id}")
                demo_bundle = DemoFHIRService.get_active_medications(patient_id)
                if demo_bundle is None:
                    demo_bundle = FHIRBundle(resourceType="Bundle", type="searchset", total=0, entry=[])
                active_medication_names = self._extract_medication_names(demo_bundle)
                logger.info(
                    f"Retrieved {len(active_medication_names)} demo medications: "
                    f"{', '.join(active_medication_names)}"
                )
            else:
                # Fetch active medications from FHIR service
                active_medication_names = None
                if self.fhir_service:
                    try:
                        logger.info(
                            f"Fetching active medications from FHIR for patient {patient_id}"
                        )
                        fhir_bundle = await self.fhir_service.get_active_medications(patient_id)
                        active_medication_names = self._extract_medication_names(fhir_bundle)
                        logger.info(
                            f"Retrieved {len(active_medication_names)} active medications: "
                            f"{', '.join(active_medication_names)}"
                        )
                    except (FHIRConnectionError, FHIRAuthenticationError) as e:
                        logger.error(
                            f"Failed to fetch medications from FHIR: {e}. "
                            f"Cannot generate alerts without active medication list."
                        )
                        # Return empty alerts if FHIR fails
                        return ClinicalAlertResponse(
                            patient_id=patient_id,
                            red_alerts=[],
                            yellow_alerts=[],
                            green_alerts=[],
                            grey_alerts=[]
                        )
            
            # Retrieve patient's phenotype profile
            phenotype_profile = await self.phenotype_service.get_clinical_profile(
                patient_id
            )
            
            logger.info(
                f"Retrieved phenotype profile with {len(phenotype_profile)} genes"
            )
            
            # Query CPIC for each gene-phenotype pair
            all_recommendations: List[DrugRecommendation] = []
            
            for gene, profile in phenotype_profile.items():
                phenotype = profile["phenotype"]
                data_available = profile["data_available"]
                
                # Skip genes with missing data (will be handled as GREY)
                if not data_available or phenotype == "Data Missing/Unknown":
                    logger.info(
                        f"Skipping CPIC query for {gene} - genomic data missing"
                    )
                    continue
                
                # Query CPIC for recommendations
                gene_recommendations = await self._fetch_gene_recommendations(
                    gene=gene,
                    phenotype=phenotype
                )
                
                all_recommendations.extend(gene_recommendations)
                
                logger.info(
                    f"Retrieved {len(gene_recommendations)} recommendations "
                    f"for {gene} ({phenotype})"
                )
            
            # Filter to only active medications
            if active_medication_names:
                original_count = len(all_recommendations)
                all_recommendations = [
                    rec for rec in all_recommendations
                    if self._medication_matches(rec.drug_name, active_medication_names)
                ]
                filtered_count = len(all_recommendations)
                logger.info(
                    f"Filtered {original_count} recommendations to "
                    f"{filtered_count} active medications"
                )
            else:
                # No active medications found
                logger.info(f"No active medications found for patient {patient_id}")
                return ClinicalAlertResponse(
                    patient_id=patient_id,
                    red_alerts=[],
                    yellow_alerts=[],
                    green_alerts=[],
                    grey_alerts=[]
                )
            
            # Categorize into Traffic Light alerts
            genes_in_profile = list(phenotype_profile.keys())
            substrate_results = await asyncio.gather(
                *[self._get_gene_substrates(g) for g in genes_in_profile],
                return_exceptions=True
            )
            gene_substrates: Dict[str, List[str]] = {
                gene: (result if isinstance(result, list) else [])
                for gene, result in zip(genes_in_profile, substrate_results)
            }

            alert_response = self._categorize_alerts(
                recommendations=all_recommendations,
                patient_id=patient_id,
                phenotype_profile=phenotype_profile,
                active_medication_names=active_medication_names,
                gene_substrates=gene_substrates
            )
            
            # Sort alerts alphabetically by drug name within each category
            alert_response.red_alerts.sort(key=lambda x: x.drug_name)
            alert_response.yellow_alerts.sort(key=lambda x: x.drug_name)
            alert_response.green_alerts.sort(key=lambda x: x.drug_name)
            alert_response.grey_alerts.sort(key=lambda x: x.drug_name)
            
            logger.info(
                f"Generated {alert_response.total_medications} alerts: "
                f"RED={len(alert_response.red_alerts)}, "
                f"YELLOW={len(alert_response.yellow_alerts)}, "
                f"GREEN={len(alert_response.green_alerts)}, "
                f"GREY={len(alert_response.grey_alerts)}"
            )
            
            return alert_response
        
        except GenomicConnectionError:
            # Re-raise database errors for graceful failure
            raise
        
        except PhenotypeCalculationError as e:
            logger.error(
                f"Phenotype calculation failed: {e.message}",
                exc_info=True
            )
            raise RecommendationServiceError(
                message="Failed to generate clinical alerts - phenotype error",
                details=e.message
            )
        
        except Exception as e:
            logger.error(
                f"Unexpected error generating clinical alerts: {e}",
                exc_info=True
            )
            raise RecommendationServiceError(
                message="Failed to generate clinical alerts",
                details=str(e)
            )
    
    async def _get_gene_substrates(self, gene: str) -> List[str]:
        """
        Return all drug names paired with this gene according to CPIC.
        """
        if gene not in self._gene_substrates_cache:
            self._gene_substrates_cache[gene] = (
                await self.cpic_service.fetch_gene_substrates(gene)
            )
        return self._gene_substrates_cache[gene]

    def _normalize_med_name(self, raw_name: str) -> str:
        """
        Strip dosage/form information from a Cerner medication display string.
        """
        # Format 1: "generic name (product description)" — strip parens and contents
        name = raw_name.split('(')[0].strip()
        # Format 2: trailing numeric dosage like "500 mg", "10 mcg/mL", "20 units"
        name = re.sub(
            r'\s+\d[\d.,]*\s*(mg|mcg|mcg/mL|mL|g|units?|%|IU)\b.*',
            '',
            name,
            flags=re.IGNORECASE
        ).strip()
        return name if name else raw_name

    async def _fetch_gene_recommendations(
        self,
        gene: str,
        phenotype: str
    ) -> List[DrugRecommendation]:
        """
        Fetch CPIC recommendations for a single gene-phenotype pair.
        """
        try:
            # Try CPIC API first
            cpic_recommendations = await self.cpic_service.fetch_recommendations(
                gene=gene,
                phenotype=phenotype
            )
            
            # Convert CPIC API response to DrugRecommendation objects
            recommendations = [
                self._convert_to_drug_recommendation(rec, phenotype)
                for rec in cpic_recommendations
            ]
            
            logger.info(
                f"Retrieved {len(recommendations)} recommendations from CPIC API "
                f"for {gene} ({phenotype})"
            )
            
            return recommendations
        
        except CPICDataNotFoundError:
            # CPIC API returned no Level A/B data – try local fallback before giving up
            logger.warning(
                f"No Level A/B recommendations from CPIC API for {gene} ({phenotype}). "
                f"Attempting fallback to local guidelines."
            )
            if is_fallback_available(gene):
                fallback = self._use_fallback_guidelines(gene, phenotype)
                if fallback:
                    return fallback
            # Neither API nor fallback had data – signal empty
            return []

        except (CPICConnectionError, CPICAPIError) as e:
            # CPIC API failed - fallback to local guidelines
            logger.warning(
                f"CPIC API failed for {gene} ({phenotype}): {e.message}. "
                f"Attempting fallback to local guidelines."
            )
            
            if is_fallback_available(gene):
                return self._use_fallback_guidelines(gene, phenotype)
            else:
                logger.error(
                    f"No fallback guidelines available for {gene}"
                )
                return []
    
    def _use_fallback_guidelines(
        self,
        gene: str,
        phenotype: str
    ) -> List[DrugRecommendation]:
        """
        Use local fallback guidelines when CPIC API is unavailable.
        """
        fallback_data = get_fallback_recommendations(gene, phenotype)
        
        if not fallback_data:
            logger.warning(
                f"No fallback guidelines found for {gene} ({phenotype})"
            )
            return []
        
        recommendations = []
        for item in fallback_data:
            drug_name = item.get("drugname", "Unknown")
            recommendation_text = item.get("recommendation", "")
            classification = item.get("classification", "Unspecified")
            guideline = item.get("guideline", {})
            guideline_level = guideline.get("level", "Unknown")
            guideline_url = guideline.get("url", "https://cpicpgx.org/guidelines/")
            
            # Determine alert color
            alert_color = self._determine_alert_color(
                recommendation_text,
                classification,
                phenotype
            )
            
            recommendations.append(
                DrugRecommendation(
                    drug_name=drug_name,
                    gene_symbol=gene,
                    phenotype=phenotype,
                    alert_color=alert_color,
                    clinical_action=recommendation_text,
                    guideline_url=guideline_url,
                    classification=classification,
                    guideline_level=guideline_level
                )
            )
        
        logger.info(
            f"Retrieved {len(recommendations)} recommendations from "
            f"fallback guidelines for {gene} ({phenotype})"
        )
        
        return recommendations
    
    def _convert_to_drug_recommendation(
        self,
        cpic_rec: CPICRecommendation,
        phenotype: str
    ) -> DrugRecommendation:
        """
        Convert CPICRecommendation to DrugRecommendation with Traffic Light color.
        """
        alert_color = self._determine_alert_color(
            cpic_rec.recommendation,
            cpic_rec.classification,
            phenotype
        )
        
        return DrugRecommendation(
            drug_name=cpic_rec.drug_name,
            gene_symbol=cpic_rec.gene_symbol,
            phenotype=phenotype,
            alert_color=alert_color,
            clinical_action=cpic_rec.recommendation,
            guideline_url=cpic_rec.guideline_url,
            classification=cpic_rec.classification,
            guideline_level=cpic_rec.guideline_level
        )
    
    def _determine_alert_color(
        self,
        recommendation: str,
        classification: str,
        phenotype: str = ""
    ) -> AlertColor:
        """
        Determine Traffic Light color based on recommendation text, classification,
        and phenotype.
        """
        recommendation_lower = recommendation.lower()
        classification_lower = classification.lower()
        phenotype_lower = phenotype.lower()

        # RED: High Risk (avoid, contraindicated, alternative)
        is_poor_phenotype = "poor" in phenotype_lower
        red_keywords = ["avoid", "contraindicated", "alternative"]
        if any(keyword in recommendation_lower for keyword in red_keywords):
            if "strong" in classification_lower or is_poor_phenotype:
                return "RED"
            else:
                return "YELLOW"
        
        # YELLOW: Moderate Risk (dose adjustment, monitoring, etc.)
        yellow_keywords = [
            "dose reduction",
            "reduction of",
            "lower dose",
            "adjustment",
            "adjust",
            "monitor",
            "titrate",
            "caution"
        ]
        if any(keyword in recommendation_lower for keyword in yellow_keywords):
            if is_poor_phenotype:
                return "RED"
            return "YELLOW"
        
        # GREEN: No Known Interaction (standard, label-recommended, no change)
        green_keywords = [
            "standard",
            "label-recommended",
            "no change",
            "initiate therapy",
            "use label"
        ]
        if any(keyword in recommendation_lower for keyword in green_keywords):
            return "GREEN"
        
        # Default to YELLOW for uncertain cases
        logger.warning(
            f"Could not determine alert color for recommendation: "
            f"'{recommendation[:50]}...' - defaulting to YELLOW"
        )
        return "YELLOW"
    
    def _categorize_alerts(
        self,
        recommendations: List[DrugRecommendation],
        patient_id: str,
        phenotype_profile: Dict[str, Dict[str, Any]],
        active_medication_names: Optional[List[str]] = None,
        gene_substrates: Optional[Dict[str, List[str]]] = None
    ) -> ClinicalAlertResponse:
        """
        Categorize drug recommendations into Traffic Light buckets.
        """
        red_alerts: List[DrugRecommendation] = []
        yellow_alerts: List[DrugRecommendation] = []
        green_alerts: List[DrugRecommendation] = []
        grey_alerts: List[DrugRecommendation] = []
        
        # Categorize existing recommendations
        for rec in recommendations:
            if rec.alert_color == "RED":
                red_alerts.append(rec)
            elif rec.alert_color == "YELLOW":
                yellow_alerts.append(rec)
            elif rec.alert_color == "GREEN":
                green_alerts.append(rec)
            elif rec.alert_color == "GREY":
                grey_alerts.append(rec)
        
        # Track which genes produced at least one recommendation (any color)
        genes_with_recommendations = {rec.gene_symbol for rec in recommendations}
        
        # Handle GREY status for missing genomic data
        for gene, profile in phenotype_profile.items():
            # Determine affected medications
            known_substrates = (gene_substrates or {}).get(gene, [])
            affected = sorted([
                m for m in (active_medication_names or [])
                if any(
                    m.lower() == sub.lower() or
                    (len(m.split()[0]) > 4 and m.split()[0].lower() == sub.split()[0].lower())
                    for sub in known_substrates
                )
            ])

            if not profile["data_available"]:
                # Request genomic testing if patient has no genomic data
                grey_alerts.append(DrugRecommendation(
                    drug_name=f"All {gene}-metabolized medications",
                    gene_symbol=gene,
                    phenotype="Data Missing/Unknown",
                    alert_color="GREY",
                    clinical_action=(
                        f"Action Required: Order genomic testing for {gene}. "
                        f"Unable to provide pharmacogenomic guidance without genotype data."
                    ),
                    guideline_url="https://cpicpgx.org/guidelines/",
                    classification="Data Missing",
                    guideline_level="N/A",
                    affected_medications=affected if affected else None
                ))
            elif gene not in genes_with_recommendations:
                # Genomic data exists but no CPIC Level A/B guidelines matched current meds
                phenotype = profile.get("phenotype", "Unknown")
                grey_alerts.append(DrugRecommendation(
                    drug_name=f"No CPIC Guidelines – {gene}",
                    gene_symbol=gene,
                    phenotype=phenotype,
                    alert_color="GREY",
                    clinical_action=(
                        f"No CPIC Level A/B clinical guidelines available for {gene} "
                        f"({phenotype}) with current medications. "
                        f"Consult a clinical pharmacist before prescribing."
                    ),
                    guideline_url=f"https://cpicpgx.org/genes-drugs/",
                    classification="No CPIC Level A/B Guidelines",
                    guideline_level="N/A",
                    affected_medications=None
                ))
        
        total_medications = len(active_medication_names) if active_medication_names else len(red_alerts) + len(yellow_alerts) + len(green_alerts)
        
        return ClinicalAlertResponse(
            patient_id=patient_id,
            red_alerts=red_alerts,
            yellow_alerts=yellow_alerts,
            green_alerts=green_alerts,
            grey_alerts=grey_alerts,
            active_medications=sorted(active_medication_names) if active_medication_names else [],
            total_medications=total_medications
        )
    
    async def get_genomic_summary(
        self,
        patient_id: str
    ) -> GenomicProfileSummary:
        """
        Generate genomic profile summary for dashboard overview.
        """
        phenotype_profile = await self.phenotype_service.get_clinical_profile(
            patient_id
        )
        
        genes_analyzed: List[str] = []
        genes_missing: List[str] = []
        phenotypes: Dict[str, str] = {}
        
        for gene, profile in phenotype_profile.items():
            phenotypes[gene] = profile["phenotype"]
            
            if profile["data_available"]:
                genes_analyzed.append(gene)
            else:
                genes_missing.append(gene)
        
        return GenomicProfileSummary(
            patient_id=patient_id,
            genes_analyzed=genes_analyzed,
            genes_missing=genes_missing,
            phenotypes=phenotypes
        )
    
    def _extract_medication_names(self, fhir_bundle: FHIRBundle) -> List[str]:
        """
        Extract medication names from FHIR Bundle response.
        """
        seen: set = set()
        medication_names = []
        
        if not fhir_bundle.entry:
            logger.warning("FHIR Bundle contains no entries")
            return medication_names
        
        for entry in fhir_bundle.entry:
            if not entry.resource:
                continue
            
            resource = entry.resource
            resource_type = resource.get("resourceType")
            
            if resource_type != "MedicationRequest":
                continue
            
            # Extract medication name
            medication_name = None
            
            if "medicationCodeableConcept" in resource:
                med_concept = resource["medicationCodeableConcept"]
                if "text" in med_concept:
                    medication_name = med_concept["text"]
                elif "coding" in med_concept and len(med_concept["coding"]) > 0:
                    medication_name = med_concept["coding"][0].get("display")
            
            elif "medicationReference" in resource:
                med_ref = resource["medicationReference"]
                if "display" in med_ref:
                    medication_name = med_ref["display"]
            
            if medication_name:
                normalized = self._normalize_med_name(medication_name).lower()
                if normalized not in seen:
                    seen.add(normalized)
                    medication_names.append(normalized)
        
        logger.info(f"Extracted {len(medication_names)} unique medication names from FHIR Bundle")
        return medication_names
    
    def _medication_matches(self, drug_name: str, active_medications: List[str]) -> bool:
        """
        Check if a drug name matches any active medication.
        """
        drug_normalized = drug_name.strip().lower()
        
        for active_med in active_medications:
            # Exact match
            if drug_normalized == active_med:
                return True
            
            # First-word match
            drug_base = drug_normalized.split()[0]
            active_base = active_med.split()[0]
            if len(drug_base) > 4 and drug_base == active_base:
                return True
        
        return False


# Factory Function
def create_recommendation_service() -> RecommendationService:
    """
    Factory function to create a RecommendationService instance.
    """
    return RecommendationService()
