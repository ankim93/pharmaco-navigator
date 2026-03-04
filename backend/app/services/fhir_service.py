"""
FHIR Service for Cerner EHR Integration.
Handles asynchronous communication with Cerner FHIR R4 API for patient demographic retrieval and active medication list synchronization.
"""

from typing import Optional
import httpx
from fastapi import HTTPException, status
from app.models.schemas import FHIRPatient, FHIRBundle


# Custom Exceptions (Graceful Failure)
class FHIRServiceError(Exception):
    """
    Base exception for FHIR service errors.
    """
    pass


class FHIRConnectionError(FHIRServiceError):
    """
    Raised when unable to connect to Cerner FHIR API.
    """
    def __init__(self, message: str = "Unable to connect to FHIR server"):
        self.message = message
        super().__init__(self.message)


class FHIRAuthenticationError(FHIRServiceError):
    """
    Raised when FHIR API rejects authentication credentials.
    """
    def __init__(self, message: str = "FHIR authentication failed"):
        self.message = message
        super().__init__(self.message)


class FHIRResourceNotFoundError(FHIRServiceError):
    """
    Raised when requested FHIR resource does not exist.
    """
    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(self.message)


class FHIRValidationError(FHIRServiceError):
    """
    Raised when FHIR response cannot be validated against Pydantic schema.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# FHIR Service Class
class FHIRService:
    """
    Asynchronous FHIR R4 client for Cerner EHR integration.
    """
    
    def __init__(self, access_token: str, fhir_base_url: str):
        """
        Initialize FHIR service with session credentials.
        """
        self.access_token = access_token
        self.fhir_base_url = fhir_base_url.rstrip('/') 
        self.timeout = 10.0  # Seconds
    
    def _get_headers(self) -> dict[str, str]:
        """
        Construct HTTP headers with Bearer token authentication.
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/fhir+json",  # FHIR R4 MIME type
            "Content-Type": "application/fhir+json"
        }
    
    async def get_patient_demographics(self, patient_id: str) -> FHIRPatient:
        """
        Retrieve patient demographic data from Cerner FHIR API.
        """
        endpoint = f"{self.fhir_base_url}/Patient/{patient_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                # Handle HTTP error responses
                if response.status_code == 401 or response.status_code == 403:
                    raise FHIRAuthenticationError(
                        "Access token invalid or expired - re-authentication required"
                    )
                
                if response.status_code == 404:
                    raise FHIRResourceNotFoundError("Patient", patient_id)
                
                if response.status_code >= 500:
                    raise FHIRConnectionError(
                        f"Cerner FHIR server error: HTTP {response.status_code}"
                    )
                
                if response.status_code != 200:
                    raise FHIRConnectionError(
                        f"Unexpected FHIR response: HTTP {response.status_code}"
                    )
                
                # Parse and validate response with Pydantic
                try:
                    patient_data = FHIRPatient.model_validate(response.json())
                    return patient_data
                
                except Exception as e:
                    raise FHIRValidationError(
                        f"Invalid Patient resource structure: {str(e)}"
                    )
        
        except httpx.TimeoutException:
            raise FHIRConnectionError(
                "FHIR request timed out - Cerner server not responding"
            )
        
        except httpx.ConnectError as e:
            raise FHIRConnectionError(
                f"Unable to connect to Cerner FHIR server: {str(e)}"
            )
        
        except httpx.RequestError as e:
            raise FHIRConnectionError(
                f"Network error during FHIR request: {str(e)}"
            )
    
    async def get_active_medications(self, patient_id: str) -> FHIRBundle:
        """
        Retrieve active medication list for a patient from Cerner FHIR API.
        """
        # Construct FHIR search query for active medications
        endpoint = f"{self.fhir_base_url}/MedicationRequest"
        params = {
            "patient": patient_id,
            "status": "active",
            "_format": "json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params=params,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                # Handle HTTP error responses
                if response.status_code == 401 or response.status_code == 403:
                    raise FHIRAuthenticationError(
                        "Access token invalid or expired - re-authentication required"
                    )
                
                if response.status_code >= 500:
                    raise FHIRConnectionError(
                        f"Cerner FHIR server error: HTTP {response.status_code}"
                    )
                
                if response.status_code != 200:
                    raise FHIRConnectionError(
                        f"Unexpected FHIR response: HTTP {response.status_code}"
                    )
                
                # Parse and validate Bundle response
                try:
                    bundle_data = FHIRBundle.model_validate(response.json())
                    return bundle_data
                
                except Exception as e:
                    raise FHIRValidationError(
                        f"Invalid Bundle resource structure: {str(e)}"
                    )
        
        except httpx.TimeoutException:
            raise FHIRConnectionError(
                "FHIR request timed out - Cerner server not responding"
            )
        
        except httpx.ConnectError as e:
            raise FHIRConnectionError(
                f"Unable to connect to Cerner FHIR server: {str(e)}"
            )
        
        except httpx.RequestError as e:
            raise FHIRConnectionError(
                f"Network error during FHIR request: {str(e)}"
            )
    

# Helper Functions
def create_fhir_service(access_token: str, fhir_base_url: str) -> FHIRService:
    """
    Factory function to create FHIRService instance.
    """
    return FHIRService(access_token=access_token, fhir_base_url=fhir_base_url)
