"""
Patient Clinical Insights API Endpoints.
Exposes PhenotypeService and RecommendationService to the frontend for real-time decision support.
"""

from fastapi import APIRouter, HTTPException, status, Request
from typing import Dict, Any, Optional
import logging
from app.core.config import Settings
from app.models.recommendation import (
    ClinicalAlertResponse,
    GenomicProfileSummary,
)
from app.services.phenotype_service import (
    create_phenotype_service,
    PhenotypeCalculationError,
)
from app.services.recommendation_service import (
    RecommendationService,
    create_recommendation_service,
    RecommendationServiceError,
)
from app.services.fhir_service import FHIRService
from app.services.genomic_service import (
    GenomicConnectionError,
    GenomicDataNotFoundError,
)
from app.services.cpic_service import (
    CPICConnectionError,
    CPICAPIError,
)


# Configure logging
logger = logging.getLogger(__name__)

# Load configuration
settings = Settings()  # type: ignore[call-arg]

# Initialize router
router = APIRouter()

# Initialize services (singleton instances for efficiency)
phenotype_service = create_phenotype_service()

# FHIR service for medication filtering
def get_recommendation_service(request: Request) -> RecommendationService:
    """
    Factory to create RecommendationService with FHIR integration.
    """
    # Extract access token from session if available
    session = request.session if hasattr(request, 'session') else {}
    access_token = session.get('access_token')
    
    if not access_token:
        access_token = settings.CERNER_CLIENT_ID
        logger.info("Using client_id as access token for FHIR service")
    
    fhir_service = FHIRService(
        access_token=access_token,
        fhir_base_url=settings.CERNER_FHIR_BASE_URL
    )
    logger.info("FHIR service initialized for medication filtering")
    
    return RecommendationService(
        phenotype_service=phenotype_service,
        fhir_service=fhir_service
    )


# Patient Clinical Insights Endpoints
@router.get(
    "/patient/{patient_id}/summary",
    response_model=GenomicProfileSummary,
    tags=["Patient Clinical Insights"],
    summary="Get Patient Genomic Profile Summary",
    description=(
        "Retrieves a comprehensive summary of the patient's genomic profile "
        "including analyzed genes, missing genes, and translated phenotypes."
    ),
    responses={
        200: {
            "description": "Genomic profile summary retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "patient_id": "12724067",
                        "genes_analyzed": ["CYP2D6", "CYP2C19"],
                        "genes_missing": ["SLCO1B1", "ABCB1"],
                        "phenotypes": {
                            "CYP2D6": "Intermediate Metabolizer",
                            "CYP2C19": "Normal Metabolizer",
                            "SLCO1B1": "Data Missing/Unknown",
                            "ABCB1": "Data Missing/Unknown"
                        }
                    }
                }
            }
        },
        404: {
            "description": "Patient not found in genomic database",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No genomic data found for patient_id='unknown-patient'"
                    }
                }
            }
        },
        503: {
            "description": "Database connection unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Unable to connect to Azure PostgreSQL database"
                    }
                }
            }
        }
    }
)
async def get_patient_genomic_summary(patient_id: str) -> GenomicProfileSummary:
    """
    Get comprehensive genomic profile summary for a patient.
    """
    logger.info(f"GET /patient/{patient_id}/summary - Fetching genomic profile")
    
    try:
        # Create basic recommendation service (no FHIR needed for summary)
        service = create_recommendation_service()
        summary = await service.get_genomic_summary(patient_id)
        
        logger.info(
            f"Successfully retrieved genomic summary for patient_id='{patient_id}' - "
            f"Genes analyzed: {len(summary.genes_analyzed)}, "
            f"Genes missing: {len(summary.genes_missing)}"
        )
        
        return summary
    
    except GenomicDataNotFoundError as e:
        # Patient exists but has no genomic data in database
        logger.warning(f"No genomic data found for patient_id='{patient_id}': {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No genomic data found for patient_id='{patient_id}'. "
                   f"Genomic testing may not have been ordered or results not yet available."
        )
    
    except GenomicConnectionError as e:
        # Database connection failed (Azure PostgreSQL unavailable)
        logger.error(f"Database connection error for patient_id='{patient_id}': {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to connect to genomic database. Please try again later."
        )
    
    except PhenotypeCalculationError as e:
        # Phenotype calculation failed (unexpected data format)
        logger.error(f"Phenotype calculation error for patient_id='{patient_id}': {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating phenotypes: {e.message}"
        )
    
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error retrieving genomic summary for patient_id='{patient_id}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing genomic data"
        )


@router.get(
    "/patient/{patient_id}/alerts",
    response_model=ClinicalAlertResponse,
    tags=["Patient Clinical Insights"],
    summary="Generate Clinical Decision Support Alerts",
    description=(
        "Generates Traffic Light clinical alerts for drug-gene interactions "
        "by cross-referencing patient phenotypes with CPIC guidelines.\n\n"
        "**Traffic Light System:**\n"
        "- **RED**: High Risk - alternative therapy or significant dose adjustment required\n"
        "- **YELLOW**: Moderate Risk - caution, monitoring, or dose titration recommended\n"
        "- **GREEN**: No Known Interaction - standard label-recommended dosing safe\n"
        "- **GREY**: Genomic Data Missing - unable to analyze, order genomic testing\n\n"
    ),
    responses={
        200: {
            "description": "Clinical alerts generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "patient_id": "12724067",
                        "red_alerts": [
                            {
                                "drug_name": "Codeine",
                                "gene_symbol": "CYP2D6",
                                "phenotype": "Poor Metabolizer",
                                "alert_color": "RED",
                                "clinical_action": "Avoid codeine use due to lack of efficacy; use alternative analgesic (e.g., morphine, hydromorphone)",
                                "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/",
                                "classification": "Strong",
                                "guideline_level": "A"
                            }
                        ],
                        "yellow_alerts": [
                            {
                                "drug_name": "Simvastatin",
                                "gene_symbol": "SLCO1B1",
                                "phenotype": "Decreased Function",
                                "alert_color": "YELLOW",
                                "clinical_action": "Lower simvastatin dose (<40mg daily) or consider alternative statin (pravastatin, rosuvastatin)",
                                "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/",
                                "classification": "Moderate",
                                "guideline_level": "A"
                            }
                        ],
                        "green_alerts": [
                            {
                                "drug_name": "Tramadol",
                                "gene_symbol": "CYP2D6",
                                "phenotype": "Normal Metabolizer",
                                "alert_color": "GREEN",
                                "clinical_action": "Use label-recommended age- or weight-specific dosing.",
                                "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/",
                                "classification": "Standard",
                                "guideline_level": "A"
                            }
                        ],
                        "grey_alerts": [],
                        "total_medications": 3
                    }
                }
            }
        },
        404: {
            "description": "Patient not found in genomic database"
        },
        503: {
            "description": "Database or CPIC API unavailable (fallback guidelines used)"
        }
    }
)
async def get_patient_clinical_alerts(
    patient_id: str,
    request: Request
) -> ClinicalAlertResponse:
    """
    Generate Traffic Light clinical decision support alerts for a patient.
    """
    logger.info(f"GET /patient/{patient_id}/alerts - Generating clinical alerts")
    
    try:
        # Create recommendation service with FHIR integration
        recommendation_service = get_recommendation_service(request)
        
        # Generate Traffic Light alerts (filtered to active medications)
        alerts = await recommendation_service.generate_clinical_alerts(
            patient_id=patient_id
        )
        
        logger.info(
            f"Successfully generated alerts for patient_id='{patient_id}' - "
            f"RED: {len(alerts.red_alerts)}, "
            f"YELLOW: {len(alerts.yellow_alerts)}, "
            f"GREEN: {len(alerts.green_alerts)}, "
            f"GREY: {len(alerts.grey_alerts)}"
        )
        
        return alerts
    
    except GenomicDataNotFoundError as e:
        # Patient exists but has no genomic data
        logger.warning(f"No genomic data for patient_id='{patient_id}': {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No genomic data found for patient_id='{patient_id}'. "
                   f"Unable to generate clinical alerts without genomic testing results."
        )
    
    except GenomicConnectionError as e:
        # Database connection failed
        logger.error(f"Database connection error for patient_id='{patient_id}': {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Genomic database unavailable. Please try again later."
        )
    
    except (CPICConnectionError, CPICAPIError) as e:
        # CPIC API failed - service should have handled fall back internally
        logger.error(
            f"CPIC API unavailable for patient_id='{patient_id}' and fallback failed: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CPIC API and fallback guidelines unavailable. Unable to generate alerts."
        )
    
    except RecommendationServiceError as e:
        # Recommendation generation failed
        logger.error(f"Alert generation error for patient_id='{patient_id}': {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating clinical alerts: {e.message}"
        )
    
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error generating alerts for patient_id='{patient_id}'")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating clinical alerts"
        )


# Health Check Endpoint
@router.get(
    "/health",
    tags=["Patient Clinical Insights"],
    summary="Health Check with Service Dependencies",
    description=(
        "Comprehensive health check that validates connections to:\n"
        "- Azure PostgreSQL Database (genomic data)\n"
        "- CPIC API (pharmacogenomic guidelines)\n\n"
        "Returns detailed status for monitoring and troubleshooting."
    ),
    responses={
        200: {
            "description": "All services healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "services": {
                            "database": {
                                "status": "connected",
                                "message": "Azure PostgreSQL connection successful"
                            },
                            "cpic_api": {
                                "status": "available",
                                "message": "CPIC API responding normally"
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "One or more services unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "status": "degraded",
                        "services": {
                            "database": {
                                "status": "connected",
                                "message": "Azure PostgreSQL connection successful"
                            },
                            "cpic_api": {
                                "status": "unavailable",
                                "message": "Connection timeout - using fallback guidelines"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check for all service dependencies.
    """
    logger.info("Running comprehensive health check")
    
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check Azure PostgreSQL Database
    try:
        # Use GenomicService to test database connection
        from app.services.genomic_service import create_genomic_service
        genomic_service = create_genomic_service()
        
        # Try a simple query with a test patient ID that may or may not exist
        try:
            await genomic_service.get_patient_genotypes("health-check-test")
        except GenomicDataNotFoundError:
            # Expected - test patient doesn't exist, but connection works
            pass
        
        health_status["services"]["database"] = {
            "status": "connected",
            "message": "Azure PostgreSQL connection successful"
        }
    
    except GenomicConnectionError as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = {
            "status": "unavailable",
            "message": f"Database connection failed: {e.message}"
        }
        logger.error(f"Health check - Database unavailable: {e.message}")
    
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = {
            "status": "error",
            "message": f"Unexpected database error: {str(e)}"
        }
        logger.exception("Health check - Unexpected database error")
    
    # Check CPIC API
    try:
        # Create service to test CPIC API connection
        service = create_recommendation_service()
        cpic_is_healthy = await service.cpic_service.check_api_health()
        
        if cpic_is_healthy:
            health_status["services"]["cpic_api"] = {
                "status": "available",
                "message": "CPIC API responding normally"
            }
        else:
            health_status["status"] = "degraded"
            health_status["services"]["cpic_api"] = {
                "status": "unavailable",
                "message": "CPIC API health check failed - fallback guidelines available"
            }
    
    except (CPICConnectionError, CPICAPIError) as e:
        health_status["status"] = "degraded"
        health_status["services"]["cpic_api"] = {
            "status": "unavailable",
            "message": f"CPIC API unavailable: {str(e)} - Fallback guidelines will be used"
        }
        logger.warning(f"Health check - CPIC API unavailable: {str(e)}")
    
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["cpic_api"] = {
            "status": "error",
            "message": f"Unexpected CPIC API error: {str(e)}"
        }
        logger.exception("Health check - Unexpected CPIC API error")
    
    # Return 503 if any service is degraded
    if health_status["status"] == "degraded":
        logger.warning("Health check - System degraded, one or more services unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    logger.info("Health check - All services healthy")
    return health_status
