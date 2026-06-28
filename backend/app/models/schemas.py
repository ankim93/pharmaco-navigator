"""
Data models for external API responses.
Provides type-safe schemas for Cerner OAuth, FHIR, RxNav, and CPIC APIs.
"""

from __future__ import annotations
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


# Cerner OAuth 2.0 / SMART on FHIR Models
class CernerTokenResponse(BaseModel):
    """
    Response from Cerner token endpoint after authorization code exchange.
    """
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    patient: str  
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None


class SessionData(BaseModel):
    """
    Type-safe session data structure storing Cerner OAuth tokens and patient context.
    """
    model_config = ConfigDict(frozen=False)  # Allow session updates
    
    access_token: str
    patient_id: str
    fhir_server_url: str
    authenticated: bool
    token_type: str = "Bearer"
    scope: str
    refresh_token: Optional[str] = None



# FHIR R4 Resource Models
class FHIRIdentifier(BaseModel):
    """
    FHIR Identifier datatype.
    """
    system: Optional[str] = None
    value: Optional[str] = None


class FHIRHumanName(BaseModel):
    """
    FHIR HumanName datatype.
    """
    family: Optional[str] = None
    given: Optional[List[str]] = None
    text: Optional[str] = None


class FHIRPatient(BaseModel):
    """
    Simplified FHIR Patient resource.
    """
    resourceType: Literal["Patient"] = "Patient"
    id: str
    identifier: Optional[List[FHIRIdentifier]] = None
    name: Optional[List[FHIRHumanName]] = None
    birthDate: Optional[str] = None
    gender: Optional[str] = None


class FHIRReference(BaseModel):
    """
    FHIR Reference datatype.
    """
    reference: Optional[str] = None
    display: Optional[str] = None


class FHIRCodeableConcept(BaseModel):
    """
    FHIR CodeableConcept datatype.
    """
    coding: Optional[List[dict[str, Any]]] = None
    text: Optional[str] = None


class FHIRMedicationRequest(BaseModel):
    """
    Simplified FHIR MedicationRequest resource.
    """
    resourceType: Literal["MedicationRequest"] = "MedicationRequest"
    id: str
    status: str
    intent: str
    medicationCodeableConcept: Optional[FHIRCodeableConcept] = None
    medicationReference: Optional[FHIRReference] = None
    subject: FHIRReference
    authoredOn: Optional[str] = None


class FHIRBundleEntry(BaseModel):
    """
    FHIR Bundle entry.
    """
    resource: dict[str, Any]  # Can be Patient, MedicationRequest, etc.
    fullUrl: Optional[str] = None


class FHIRBundle(BaseModel):
    """
    FHIR Bundle resource for search results.
    """
    resourceType: Literal["Bundle"] = "Bundle"
    type: str
    total: Optional[int] = None
    entry: Optional[List[FHIRBundleEntry]] = None


# RxNav API Models
class RxNavRxCUI(BaseModel):
    """
    RxNav RxCUI identifier.
    """
    rxcui: str
    name: str
    tty: Optional[str] = None


class RxNavDrugGroup(BaseModel):
    """
    RxNav drug group response.
    """
    name: Optional[str] = None
    conceptGroup: Optional[List[dict[str, Any]]] = None


class RxNavApproximateResponse(BaseModel):
    """
    Response from RxNav approximateTerm endpoint for medication name normalization.
    """
    approximateGroup: Optional[RxNavDrugGroup] = None


class RxNavIngredientResponse(BaseModel):
    """
    Response from RxNav to get ingredient-level RxCUI.
    """
    allRelatedGroup: Optional[dict[str, Any]] = None


# CPIC API Models
class CPICRecommendation(BaseModel):
    """
    CPIC clinical recommendation for drug-gene pair.
    """
    drug: str
    gene: str
    phenotype: str
    recommendation: str
    classification: str  # "Strong", "Moderate", etc.
    evidenceLevel: str  # "A", "B", "C", "D"
    
    # Optional fields
    activityScore: Optional[float] = None
    implications: Optional[str] = None
    alternatives: Optional[str] = None


class CPICGuideline(BaseModel):
    """
    CPIC guideline metadata.
    """
    id: str
    name: str
    drugId: str
    geneSymbol: str
    url: Optional[str] = None


class CPICGuidelineResponse(BaseModel):
    """
    Response from CPIC API guideline endpoint.
    """
    data: List[CPICGuideline]


class CPICPairResponse(BaseModel):
    """
    Response from CPIC API for drug-gene pair query.
    """
    data: List[CPICRecommendation]


# Internal Database Models (for Genotype data)
class AlleleData(BaseModel):
    """
    Star-allele genotype data from PostgreSQL.
    """
    gene: str  # e.g., "CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"
    allele1: str  # e.g., "*1", "*2", "*3"
    allele2: str  # e.g., "*1", "*2", "*3"
    diplotype: str  # e.g., "*1/*2"
    
    # Optional metadata
    score1: Optional[float] = None  # Activity score for allele1
    score2: Optional[float] = None  # Activity score for allele2


class PhenotypeResult(BaseModel):
    """
    Translated phenotype from genotype.
    """
    gene: str
    diplotype: str
    activityScore: Optional[float] = None  # For CYP enzymes
    phenotype: str  # e.g., "Poor Metabolizer", "Normal Function"
    functionalStatus: Optional[str] = None  # For transporters
    
    # Flag for missing data
    dataMissing: bool = False
    missingReason: Optional[str] = None


# Clinical Alert Models (Orchestration Output)
class MedicationAlert(BaseModel):
    """
    Individual medication safety alert.
    """
    medicationName: str
    rxcui: str
    riskLevel: Literal["high", "moderate", "none", "unknown"]
    riskColor: Literal["red", "yellow", "green", "grey"]
    
    # Drug-gene interaction details
    affectedGenes: List[str]
    phenotypes: List["PhenotypeResult"]
    recommendation: str
    evidenceLevel: str
    
    # Additional context
    alternatives: Optional[str] = None
    actionRequired: Optional[str] = None 


class AlertDashboard(BaseModel):
    """
    Complete dashboard response for frontend.
    """
    patientId: str
    timestamp: str
    
    # Categorized alerts
    highRisk: List["MedicationAlert"] = Field(default_factory=list)
    moderateRisk: List["MedicationAlert"] = Field(default_factory=list)
    noRisk: List["MedicationAlert"] = Field(default_factory=list)
    dataMissing: List["MedicationAlert"] = Field(default_factory=list)
    
    # Metadata
    totalMedications: int
    genomicDataComplete: bool
    errors: List[str] = Field(default_factory=list)


# API Response Models
class SessionStatusResponse(BaseModel):
    """
    Response for /auth/session endpoint.
    """
    authenticated: bool
    patientId: Optional[str] = None
    expiresIn: Optional[int] = None
    message: Optional[str] = None


class LogoutResponse(BaseModel):
    """
    Response for /auth/logout endpoint.
    """
    status: Literal["logged_out"]
    message: str


class HealthCheckResponse(BaseModel):
    """
    Response for health check endpoints.
    """
    status: str
    service: Optional[str] = None
    fhirEnabled: Optional[bool] = None
    application: Optional[str] = None
    environment: Optional[str] = None
    version: Optional[str] = None


# Error Response Models
class ErrorDetail(BaseModel):
    """
    Structured error detail.
    """
    code: str
    message: str
    field: Optional[str] = None


class ServiceErrorResponse(BaseModel):
    """
    Response when external service fails.
    """
    error: str
    service: str  # "Cerner", "RxNav", "CPIC", "Database"
    detail: str
    failureMode: Literal["graceful", "critical"]


# =========================================================================== #
# Phase 2 — Perimeter input guardrails                                        #
# =========================================================================== #

_SCOPE_PANEL: frozenset[str] = frozenset({"CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"})


class GenotypeInputModel(BaseModel):
    """
    Perimeter gate for raw genotype write payloads.

    Validators run at the boundary before any service or database layer is
    touched — invalid data is rejected with a 422 before it can corrupt the
    genotype table or produce a nonsensical phenotype calculation.

    Rules (applied in declaration order):
    - patient_id: stripped of leading/trailing whitespace; must be non-empty.
    - gene_symbol: stripped, forced to uppercase, must be within SCOPE_PANEL.
    - allele_1 / allele_2: stripped and forced to uppercase; must be non-empty.
    """

    patient_id: str
    gene_symbol: str
    allele_1: str
    allele_2: str

    @field_validator("patient_id")
    @classmethod
    def _clean_patient_id(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("patient_id must not be empty or whitespace-only")
        return cleaned

    @field_validator("gene_symbol")
    @classmethod
    def _validate_gene_symbol(cls, v: str) -> str:
        normalised = v.strip().upper()
        if normalised not in _SCOPE_PANEL:
            raise ValueError(
                f"gene_symbol '{normalised}' is outside the supported scope panel. "
                f"Accepted genes: {sorted(_SCOPE_PANEL)}"
            )
        return normalised

    @field_validator("allele_1", "allele_2")
    @classmethod
    def _normalise_allele(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Allele designations must not be empty or whitespace-only")
        return cleaned
