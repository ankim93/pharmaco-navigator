"""
FHIR resource endpoints.
Handles patient demographics and medication synchronization from Cerner EHR.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, status
import httpx
from app.models.schemas import FHIRPatient, FHIRBundle
from app.core.session import (
    require_authentication,
    get_authorization_header,
    get_fhir_server_url
)


router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/patient/{patient_id}")
async def get_patient(patient_id: str, request: Request) -> FHIRPatient:
    """
    Retrieve patient demographics from Cerner FHIR API.
    """
    # Verify authentication and get credentials
    require_authentication(request)
    headers: dict[str, str] = get_authorization_header(request)
    fhir_base_url: str = get_fhir_server_url(request)
    
    # Construct FHIR API endpoint
    patient_url: str = f"{fhir_base_url}/Patient/{patient_id}"
    
    try:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.get(
                patient_url,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Patient {patient_id} not found in FHIR server"
                )

            if response.status_code != 200:
                logger.error(
                    "FHIR API error fetching patient: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="FHIR data unavailable. Please try again later."
                )
            
            # Parse response with type-safe Pydantic model
            patient_data = FHIRPatient.model_validate(response.json())
            return patient_data
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="FHIR API request timed out"
        )
    except httpx.RequestError as exc:
        logger.error("FHIR connection error fetching patient: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FHIR service temporarily unavailable."
        )


@router.get("/medications/{patient_id}")
async def get_medications(patient_id: str, request: Request) -> FHIRBundle:
    """
    Retrieve active medications from Cerner FHIR API.
    """
    # Verify authentication and get credentials
    require_authentication(request)
    headers: dict[str, str] = get_authorization_header(request)
    fhir_base_url: str = get_fhir_server_url(request)
    
    # Construct FHIR search endpoint for active medications
    medications_url: str = (
        f"{fhir_base_url}/MedicationRequest"
        f"?patient={patient_id}"
        f"&status=active"
        f"&_count=100"
    )
    
    try:
        async with httpx.AsyncClient() as client:
            response: httpx.Response = await client.get(
                medications_url,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No medication records found for patient {patient_id}"
                )

            if response.status_code != 200:
                logger.error(
                    "FHIR API error fetching medications: status=%s body=%s",
                    response.status_code,
                    response.text,
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="FHIR data unavailable. Please try again later."
                )
            
            # Parse response with type-safe Pydantic model
            bundle = FHIRBundle.model_validate(response.json())
            return bundle
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="FHIR API request timed out"
        )
    except httpx.RequestError as exc:
        logger.error("FHIR connection error fetching medications: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FHIR service temporarily unavailable."
        )
