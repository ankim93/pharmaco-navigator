"""
RxNav Service for Medication Normalization.
Handles asynchronous communication with NLM RxNav API for medication name normalization to standardized RxCUI identifiers and ingredient-level extraction for CPIC guideline matching.
"""

from typing import Optional
import httpx
from app.models.schemas import RxNavApproximateResponse, RxNavRxCUI
from app.core.config import settings


# Custom Exceptions (Graceful Failure)
class RxNavServiceError(Exception):
    """
    Base exception for RxNav service errors.
    """
    pass


class RxNavConnectionError(RxNavServiceError):
    """
    Raised when unable to connect to RxNav API.
    """
    def __init__(self, message: str = "Unable to connect to RxNav API"):
        self.message = message
        super().__init__(self.message)


class RxNavNotFoundError(RxNavServiceError):
    """
    Raised when RxNav cannot find a match for the medication name.
    """
    def __init__(self, medication_name: str):
        self.medication_name = medication_name
        self.message = f"No RxCUI found for medication: '{medication_name}'"
        super().__init__(self.message)


class RxNavValidationError(RxNavServiceError):
    """
    Raised when RxNav response cannot be validated against Pydantic schema.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# RxNav Service Class
class RxNavService:
    """
    Asynchronous RxNav client for medication normalization.
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize RxNav service.
        """
        self.base_url = (base_url or settings.RXNAV_API_BASE_URL).rstrip('/')
        self.timeout = 5.0  # Seconds
    
    async def get_rxcui_for_medication(self, medication_name: str) -> str:
        """
        Normalize medication name to ingredient-level (IN) RxCUI identifier.
        """
        # Find approximate RxCUI match for medication name
        approximate_rxcui = await self._find_approximate_rxcui(medication_name)
        
        # Extract ingredient-level (IN) RxCUI
        ingredient_rxcui = await self._get_ingredient_rxcui(approximate_rxcui)
        
        return ingredient_rxcui
    
    async def _find_approximate_rxcui(self, medication_name: str) -> str:
        """
        Find the best-matching RxCUI for a medication name.
        """
        endpoint = f"{self.base_url}/approximateTerm.json"
        params = {
            "term": medication_name,
            "maxEntries": "1" 
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params=params,
                    timeout=self.timeout
                )
                
                # Handle HTTP errors
                if response.status_code >= 500:
                    raise RxNavConnectionError(
                        f"RxNav server error: HTTP {response.status_code}"
                    )
                
                if response.status_code != 200:
                    raise RxNavConnectionError(
                        f"Unexpected RxNav response: HTTP {response.status_code}"
                    )
                
                # Parse response
                data = response.json()
                
                # Extract RxCUI from response structure
                approx_group = data.get("approximateGroup")
                if not approx_group:
                    raise RxNavNotFoundError(medication_name)
                
                candidates = approx_group.get("candidate")
                if not candidates or len(candidates) == 0:
                    raise RxNavNotFoundError(medication_name)
                
                # Get first (best) match
                rxcui = candidates[0].get("rxcui")
                if not rxcui:
                    raise RxNavValidationError(
                        "RxCUI field missing from approximateTerm response"
                    )
                
                return rxcui
        
        except httpx.TimeoutException:
            raise RxNavConnectionError(
                "RxNav request timed out - service not responding"
            )
        
        except httpx.ConnectError as e:
            raise RxNavConnectionError(
                f"Unable to connect to RxNav API: {str(e)}"
            )
        
        except httpx.RequestError as e:
            raise RxNavConnectionError(
                f"Network error during RxNav request: {str(e)}"
            )
    
    async def _get_ingredient_rxcui(self, rxcui: str) -> str:
        """
        Extract ingredient-level (IN) RxCUI from a medication RxCUI.
        """
        endpoint = f"{self.base_url}/rxcui/{rxcui}/related.json"
        params = {
            "tty": "IN"  # IN = Ingredient term type
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code >= 500:
                    raise RxNavConnectionError(
                        f"RxNav server error: HTTP {response.status_code}"
                    )
                
                if response.status_code != 200:
                    raise RxNavConnectionError(
                        f"Unexpected RxNav response: HTTP {response.status_code}"
                    )
                
                # Parse response
                data = response.json()
                
                # Navigate response structure
                related_group = data.get("relatedGroup")
                if not related_group:
                    # If no related ingredients, the RxCUI might already be IN type
                    return await self._verify_ingredient_type(rxcui)
                
                concept_group = related_group.get("conceptGroup")
                if not concept_group or len(concept_group) == 0:
                    return await self._verify_ingredient_type(rxcui)
                
                # Find the IN type concept group
                for group in concept_group:
                    if group.get("tty") == "IN":
                        properties = group.get("conceptProperties")
                        if properties and len(properties) > 0:
                            ingredient_rxcui = properties[0].get("rxcui")
                            if ingredient_rxcui:
                                return ingredient_rxcui
                
                # If no IN type found in related, check if original is already IN
                return await self._verify_ingredient_type(rxcui)
        
        except httpx.TimeoutException:
            raise RxNavConnectionError(
                "RxNav request timed out - service not responding"
            )
        
        except httpx.ConnectError as e:
            raise RxNavConnectionError(
                f"Unable to connect to RxNav API: {str(e)}"
            )
        
        except httpx.RequestError as e:
            raise RxNavConnectionError(
                f"Network error during RxNav request: {str(e)}"
            )
    
    async def _verify_ingredient_type(self, rxcui: str) -> str:
        """
        Verify if a given RxCUI is already an ingredient-level (IN) type.
        """
        endpoint = f"{self.base_url}/rxcui/{rxcui}/property.json"
        params = {
            "propName": "TTY"  # Get term type
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise RxNavNotFoundError(f"RxCUI {rxcui}")
                
                data = response.json()
                prop_concept_group = data.get("propConceptGroup")
                
                if prop_concept_group:
                    prop_concept = prop_concept_group.get("propConcept")
                    if prop_concept and len(prop_concept) > 0:
                        tty = prop_concept[0].get("propValue")
                        if tty == "IN":
                            return rxcui
                
                # Not an ingredient-level RxCUI
                raise RxNavNotFoundError(
                    f"No ingredient-level RxCUI found for {rxcui}"
                )
        
        except httpx.RequestError:
            # If verification fails, raise not found
            raise RxNavNotFoundError(f"RxCUI {rxcui}")
    

# Factory Function
def create_rxnav_service(base_url: Optional[str] = None) -> RxNavService:
    """
    Factory function to create RxNavService instance.
    """
    return RxNavService(base_url=base_url)
