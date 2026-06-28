"""
Phase 2 Recommendation Service — master orchestrator for Pharmaco Navigator CDSS.

Key Phase 2 upgrades over Phase 1:
  1. asyncio.gather — phenotype profile extraction and medication context lookups
     run concurrently; neither blocks the other.
  2. 15-second timeout safety window — each outbound CPIC call is wrapped in
     asyncio.timeout(15); a TimeoutError or any network exception immediately
     triggers the local fallback guideline engine.
  3. Pessimistic Cascading Risk Escalation — if a compound has alerts at
     multiple severity tiers across overlapping pathways, the dominant
     (highest-priority) tier is applied and lower tiers are suppressed.
  4. A-Z optimisation — all four alert buckets are sorted alphabetically by
     medication name before JSON compilation.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.phenotype_service import (
    PhenotypeService,
    PhenotypeCalculationError,
    create_phenotype_service,
)
from app.services.cpic_service import (
    CPICService,
    CPICRecommendation,
    CPICConnectionError,
    CPICAPIError,
    CPICDataNotFoundError,
    create_cpic_service,
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

logger = logging.getLogger("pharmaco.navigator.recommendation")

# =========================================================================== #
# Pessimistic Cascading Risk Escalation priority map                          #
# =========================================================================== #
# RED dominates all lower tiers; GREY loses to any data-bearing tier.

_SEVERITY_RANK: dict[str, int] = {
    "RED":    3,
    "YELLOW": 2,
    "GREEN":  1,
    "GREY":   0,
}


# =========================================================================== #
# Exceptions                                                                   #
# =========================================================================== #

class RecommendationServiceError(Exception):
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)


# =========================================================================== #
# Service                                                                      #
# =========================================================================== #

class RecommendationService:
    """
    Phase 2 orchestrator for clinical decision support alerts.

    Logging identifier: "pharmaco.navigator.recommendation"
    """

    def __init__(
        self,
        phenotype_service: Optional[PhenotypeService] = None,
        cpic_service: Optional[CPICService] = None,
        fhir_service: Optional[FHIRService] = None,
    ) -> None:
        self.phenotype_service = phenotype_service or create_phenotype_service()
        self.cpic_service = cpic_service or create_cpic_service()
        self.fhir_service = fhir_service
        self._gene_substrates_cache: Dict[str, List[str]] = {}
        logger.info("RecommendationService (Phase 2) initialised")

    # ------------------------------------------------------------------ #
    # Primary entry point                                                  #
    # ------------------------------------------------------------------ #

    async def generate_clinical_alerts(
        self,
        patient_id: str,
    ) -> ClinicalAlertResponse:
        """
        Generate Traffic Light clinical alerts for *patient_id*.

        Phase 2 flow:
          1. asyncio.gather — phenotype profile + medication list fetched concurrently.
          2. Per-gene CPIC lookups — each wrapped in asyncio.timeout(15); fallback on
             TimeoutError or any network exception.
          3. Pessimistic escalation — dominant severity tier retained per compound.
          4. A-Z sort across all four alert buckets.
        """
        logger.info("Generating clinical alerts for patient_id='%s'", patient_id)

        try:
            # Phase 2: concurrent fetch — neither coroutine blocks the other.
            phenotype_profile, active_medication_names = await asyncio.gather(
                self.phenotype_service.get_clinical_profile(patient_id),
                self._fetch_active_medications(patient_id),
            )

            logger.info(
                "Concurrent fetch complete — %d genes, %d medications",
                len(phenotype_profile),
                len(active_medication_names),
            )

            if not active_medication_names:
                logger.info("No active medications found for patient '%s'", patient_id)
                return self._empty_response(patient_id)

            # Concurrent substrate lookups for GREY annotation
            genes_in_profile = list(phenotype_profile.keys())
            substrate_results = await asyncio.gather(
                *[self._get_gene_substrates(g) for g in genes_in_profile],
                return_exceptions=True,
            )
            gene_substrates: Dict[str, List[str]] = {
                gene: (result if isinstance(result, list) else [])
                for gene, result in zip(genes_in_profile, substrate_results)
            }

            # Per-gene CPIC lookups (each with 15-second timeout + fallback)
            cpic_tasks = [
                self._fetch_with_timeout(gene, profile["phenotype"])
                for gene, profile in phenotype_profile.items()
                if profile["data_available"]
                and profile["phenotype"] != "Data Missing/Unknown"
            ]
            batch_results = await asyncio.gather(*cpic_tasks, return_exceptions=True)
            all_recs: List[DrugRecommendation] = [
                rec
                for batch in batch_results
                if isinstance(batch, list)
                for rec in batch
            ]

            # Filter to active medications only
            all_recs = [
                r for r in all_recs
                if self._medication_matches(r.drug_name, active_medication_names)
            ]
            logger.info("Retained %d recommendations matching active medications", len(all_recs))

            # Phase 2: pessimistic cascading risk escalation
            escalated = self._apply_pessimistic_escalation(all_recs)

            # Categorise into four buckets
            alert_response = self._categorize_alerts(
                recommendations=escalated,
                patient_id=patient_id,
                phenotype_profile=phenotype_profile,
                active_medication_names=active_medication_names,
                gene_substrates=gene_substrates,
            )

            # A-Z optimisation — sort all buckets alphabetically by medication name
            alert_response.red_alerts.sort(key=lambda x: x.drug_name)
            alert_response.yellow_alerts.sort(key=lambda x: x.drug_name)
            alert_response.green_alerts.sort(key=lambda x: x.drug_name)
            alert_response.grey_alerts.sort(key=lambda x: x.drug_name)

            logger.info(
                "Alerts for '%s': RED=%d YELLOW=%d GREEN=%d GREY=%d",
                patient_id,
                len(alert_response.red_alerts),
                len(alert_response.yellow_alerts),
                len(alert_response.green_alerts),
                len(alert_response.grey_alerts),
            )
            return alert_response

        except GenomicConnectionError:
            raise

        except PhenotypeCalculationError as exc:
            logger.error("Phenotype calculation failed: %s", exc.message, exc_info=True)
            raise RecommendationServiceError(
                message="Failed to generate clinical alerts — phenotype error",
                details=exc.message,
            ) from exc

        except Exception as exc:
            logger.exception("Unexpected error generating clinical alerts for '%s'", patient_id)
            raise RecommendationServiceError(
                message="Failed to generate clinical alerts",
                details=str(exc),
            ) from exc

    # ------------------------------------------------------------------ #
    # Genomic summary (Phase 1 compatibility)                             #
    # ------------------------------------------------------------------ #

    async def get_genomic_summary(
        self,
        patient_id: str,
    ) -> GenomicProfileSummary:
        phenotype_profile = await self.phenotype_service.get_clinical_profile(patient_id)
        genes_analyzed: List[str] = []
        genes_missing: List[str] = []
        phenotypes: Dict[str, str] = {}

        for gene, profile in phenotype_profile.items():
            phenotypes[gene] = profile["phenotype"]
            (genes_analyzed if profile["data_available"] else genes_missing).append(gene)

        return GenomicProfileSummary(
            patient_id=patient_id,
            genes_analyzed=genes_analyzed,
            genes_missing=genes_missing,
            phenotypes=phenotypes,
        )

    # ------------------------------------------------------------------ #
    # Phase 2 — pessimistic cascading risk escalation                     #
    # ------------------------------------------------------------------ #

    def _apply_pessimistic_escalation(
        self,
        recs: List[DrugRecommendation],
    ) -> List[DrugRecommendation]:
        """
        For each compound, retain only alerts at the dominant (highest-severity) tier.

        Example: a compound with YELLOW on CYP2D6 and RED on SLCO1B1 appears in
        red_alerts only — the YELLOW entry is suppressed.  If two pathways both
        produce RED, both are preserved (gene context is retained for the clinician).
        """
        by_drug: Dict[str, List[DrugRecommendation]] = {}
        for r in recs:
            by_drug.setdefault(r.drug_name, []).append(r)

        result: List[DrugRecommendation] = []
        for drug_recs in by_drug.values():
            max_rank = max(
                _SEVERITY_RANK.get(str(r.alert_color), 0) for r in drug_recs
            )
            dominant = [
                r for r in drug_recs
                if _SEVERITY_RANK.get(str(r.alert_color), 0) == max_rank
            ]
            result.extend(dominant)
        return result

    # ------------------------------------------------------------------ #
    # CPIC fetch with 15-second timeout safety window                     #
    # ------------------------------------------------------------------ #

    async def _fetch_with_timeout(
        self,
        gene: str,
        phenotype: str,
    ) -> List[DrugRecommendation]:
        """
        Wrap the CPIC lookup in asyncio.timeout(15).  Any TimeoutError or
        network exception triggers the local fallback guideline engine.
        """
        try:
            async with asyncio.timeout(15.0):
                return await self._fetch_gene_recommendations(gene, phenotype)
        except asyncio.TimeoutError:
            logger.warning(
                "CPIC API timed out for %s (%s) after 15 s — using fallback guidelines",
                gene, phenotype,
            )
            return self._use_fallback_guidelines(gene, phenotype)

    async def _fetch_gene_recommendations(
        self,
        gene: str,
        phenotype: str,
    ) -> List[DrugRecommendation]:
        try:
            cpic_recs = await self.cpic_service.fetch_recommendations(gene=gene, phenotype=phenotype)
            recs = [self._convert_to_drug_recommendation(r, phenotype) for r in cpic_recs]
            logger.info("CPIC API: %d recommendations for %s (%s)", len(recs), gene, phenotype)
            return recs
        except CPICDataNotFoundError:
            logger.warning(
                "No Level A/B data from CPIC API for %s (%s) — trying fallback",
                gene, phenotype,
            )
            if is_fallback_available(gene):
                return self._use_fallback_guidelines(gene, phenotype)
            return []
        except (CPICConnectionError, CPICAPIError) as exc:
            logger.warning(
                "CPIC API error for %s (%s): %s — using fallback",
                gene, phenotype, exc.message,
            )
            if is_fallback_available(gene):
                return self._use_fallback_guidelines(gene, phenotype)
            logger.error("No fallback guidelines available for %s", gene)
            return []

    def _use_fallback_guidelines(
        self,
        gene: str,
        phenotype: str,
    ) -> List[DrugRecommendation]:
        fallback_data = get_fallback_recommendations(gene, phenotype)
        if not fallback_data:
            logger.warning("Fallback guidelines empty for %s (%s)", gene, phenotype)
            return []

        recs = []
        for item in fallback_data:
            drug_name = item.get("drugname", "Unknown")
            recommendation_text = item.get("recommendation", "")
            classification = item.get("classification", "Unspecified")
            guideline = item.get("guideline", {})
            alert_color = self._determine_alert_color(recommendation_text, classification, phenotype)
            recs.append(DrugRecommendation(
                drug_name=drug_name,
                gene_symbol=gene,
                phenotype=phenotype,
                alert_color=alert_color,
                clinical_action=recommendation_text,
                guideline_url=guideline.get("url", "https://cpicpgx.org/guidelines/"),
                classification=classification,
                guideline_level=guideline.get("level", "Unknown"),
            ))

        logger.info("Fallback: %d recommendations for %s (%s)", len(recs), gene, phenotype)
        return recs

    # ------------------------------------------------------------------ #
    # Medication context                                                   #
    # ------------------------------------------------------------------ #

    async def _fetch_active_medications(self, patient_id: str) -> List[str]:
        """
        Return active medication names for the patient.
        Handles demo patients, live FHIR, and graceful degradation on FHIR errors.
        """
        if DemoFHIRService.is_demo_patient(patient_id):
            logger.info("Demo patient '%s' — using synthetic medication list", patient_id)
            bundle = DemoFHIRService.get_active_medications(patient_id)
            if bundle is None:
                return []
            return self._extract_medication_names(bundle)

        if not self.fhir_service:
            return []

        try:
            bundle = await self.fhir_service.get_active_medications(patient_id)
            names = self._extract_medication_names(bundle)
            logger.info("FHIR: %d active medications for '%s'", len(names), patient_id)
            return names
        except (FHIRConnectionError, FHIRAuthenticationError) as exc:
            logger.error(
                "FHIR medication fetch failed for '%s': %s — returning empty list",
                patient_id, exc,
            )
            return []

    async def _get_gene_substrates(self, gene: str) -> List[str]:
        if gene not in self._gene_substrates_cache:
            self._gene_substrates_cache[gene] = (
                await self.cpic_service.fetch_gene_substrates(gene)
            )
        return self._gene_substrates_cache[gene]

    # ------------------------------------------------------------------ #
    # Alert construction                                                   #
    # ------------------------------------------------------------------ #

    def _categorize_alerts(
        self,
        recommendations: List[DrugRecommendation],
        patient_id: str,
        phenotype_profile: Dict[str, Dict[str, Any]],
        active_medication_names: Optional[List[str]] = None,
        gene_substrates: Optional[Dict[str, List[str]]] = None,
    ) -> ClinicalAlertResponse:
        red_alerts: List[DrugRecommendation] = []
        yellow_alerts: List[DrugRecommendation] = []
        green_alerts: List[DrugRecommendation] = []
        grey_alerts: List[DrugRecommendation] = []

        for rec in recommendations:
            color = str(rec.alert_color)
            if color == "RED":
                red_alerts.append(rec)
            elif color == "YELLOW":
                yellow_alerts.append(rec)
            elif color == "GREEN":
                green_alerts.append(rec)
            else:
                grey_alerts.append(rec)

        genes_with_recs = {rec.gene_symbol for rec in recommendations}

        for gene, profile in phenotype_profile.items():
            known_substrates = (gene_substrates or {}).get(gene, [])
            affected = sorted([
                m for m in (active_medication_names or [])
                if any(
                    m.lower() == sub.lower()
                    or (len(m.split()[0]) > 4 and m.split()[0].lower() == sub.split()[0].lower())
                    for sub in known_substrates
                )
            ])

            if not profile["data_available"]:
                grey_alerts.append(DrugRecommendation(
                    drug_name=f"All {gene}-metabolized medications",
                    gene_symbol=gene,
                    phenotype="Data Missing/Unknown",
                    alert_color="GREY",
                    clinical_action=(
                        f"Action Required: Order genomic testing for {gene}. "
                        "Unable to provide pharmacogenomic guidance without genotype data."
                    ),
                    guideline_url="https://cpicpgx.org/guidelines/",
                    classification="Data Missing",
                    guideline_level="N/A",
                    affected_medications=affected or None,
                ))
            elif gene not in genes_with_recs:
                grey_alerts.append(DrugRecommendation(
                    drug_name=f"No CPIC Guidelines – {gene}",
                    gene_symbol=gene,
                    phenotype=profile.get("phenotype", "Unknown"),
                    alert_color="GREY",
                    clinical_action=(
                        f"No CPIC Level A/B guidelines available for {gene} "
                        f"({profile.get('phenotype', 'Unknown')}) with current medications. "
                        "Consult a clinical pharmacist before prescribing."
                    ),
                    guideline_url="https://cpicpgx.org/genes-drugs/",
                    classification="No CPIC Level A/B Guidelines",
                    guideline_level="N/A",
                    affected_medications=None,
                ))

        total_medications = (
            len(active_medication_names)
            if active_medication_names
            else len(red_alerts) + len(yellow_alerts) + len(green_alerts)
        )

        return ClinicalAlertResponse(
            patient_id=patient_id,
            red_alerts=red_alerts,
            yellow_alerts=yellow_alerts,
            green_alerts=green_alerts,
            grey_alerts=grey_alerts,
            active_medications=sorted(active_medication_names) if active_medication_names else [],
            total_medications=total_medications,
        )

    def _convert_to_drug_recommendation(
        self,
        cpic_rec: CPICRecommendation,
        phenotype: str,
    ) -> DrugRecommendation:
        alert_color = self._determine_alert_color(
            cpic_rec.recommendation, cpic_rec.classification, phenotype
        )
        return DrugRecommendation(
            drug_name=cpic_rec.drug_name,
            gene_symbol=cpic_rec.gene_symbol,
            phenotype=phenotype,
            alert_color=alert_color,
            clinical_action=cpic_rec.recommendation,
            guideline_url=cpic_rec.guideline_url,
            classification=cpic_rec.classification,
            guideline_level=cpic_rec.guideline_level,
        )

    def _determine_alert_color(
        self,
        recommendation: str,
        classification: str,
        phenotype: str = "",
    ) -> AlertColor:
        rec_lower = recommendation.lower()
        cls_lower = classification.lower()
        phe_lower = phenotype.lower()
        is_poor = "poor" in phe_lower

        if any(kw in rec_lower for kw in ("avoid", "contraindicated", "alternative")):
            return "RED" if ("strong" in cls_lower or is_poor) else "YELLOW"

        if any(kw in rec_lower for kw in (
            "dose reduction", "reduction of", "lower dose",
            "adjustment", "adjust", "monitor", "titrate", "caution",
        )):
            return "RED" if is_poor else "YELLOW"

        if any(kw in rec_lower for kw in (
            "standard", "label-recommended", "no change",
            "initiate therapy", "use label",
        )):
            return "GREEN"

        logger.warning(
            "Unable to classify recommendation '%.60s...' — defaulting to YELLOW",
            recommendation,
        )
        return "YELLOW"

    # ------------------------------------------------------------------ #
    # Utility helpers                                                      #
    # ------------------------------------------------------------------ #

    def _extract_medication_names(self, fhir_bundle: FHIRBundle) -> List[str]:
        seen: set[str] = set()
        names: List[str] = []
        if not fhir_bundle.entry:
            return names
        for entry in fhir_bundle.entry:
            if not entry.resource:
                continue
            resource = entry.resource
            if resource.get("resourceType") != "MedicationRequest":
                continue
            medication_name: Optional[str] = None
            if "medicationCodeableConcept" in resource:
                concept = resource["medicationCodeableConcept"]
                medication_name = concept.get("text") or (
                    concept.get("coding", [{}])[0].get("display") if concept.get("coding") else None
                )
            elif "medicationReference" in resource:
                medication_name = resource["medicationReference"].get("display")
            if medication_name:
                normalised = self._normalize_med_name(medication_name).lower()
                if normalised not in seen:
                    seen.add(normalised)
                    names.append(normalised)
        logger.info("Extracted %d unique medication names from FHIR Bundle", len(names))
        return names

    def _normalize_med_name(self, raw_name: str) -> str:
        name = raw_name.split("(")[0].strip()
        name = re.sub(
            r"\s+\d[\d.,]*\s*(mg|mcg|mcg/mL|mL|g|units?|%|IU)\b.*",
            "",
            name,
            flags=re.IGNORECASE,
        ).strip()
        return name if name else raw_name

    def _medication_matches(self, drug_name: str, active_medications: List[str]) -> bool:
        drug_lower = drug_name.strip().lower()
        for med in active_medications:
            if drug_lower == med:
                return True
            drug_base, med_base = drug_lower.split()[0], med.split()[0]
            if len(drug_base) > 4 and drug_base == med_base:
                return True
        return False

    def _empty_response(self, patient_id: str) -> ClinicalAlertResponse:
        return ClinicalAlertResponse(
            patient_id=patient_id,
            red_alerts=[],
            yellow_alerts=[],
            green_alerts=[],
            grey_alerts=[],
        )


def create_recommendation_service() -> RecommendationService:
    return RecommendationService()
