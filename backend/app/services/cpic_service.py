"""
CPIC Service for evidence-based drug-gene screening.
Queries the CPIC API to retrieve pharmacogenomic guidelines based on gene-phenotype pairs.

"""
import logging
from typing import Dict, List, Optional, Any
import httpx


# Configure logging
logger = logging.getLogger(__name__)


# API Configuration
CPIC_API_BASE_URL = "https://api.cpicpgx.org/v1"
CPIC_RECOMMENDATION_ENDPOINT = f"{CPIC_API_BASE_URL}/recommendation"
CPIC_API_TIMEOUT = 15.0  # seconds — Phase 2 outbound safety window


# Custom Exceptions (Graceful Failure)
class CPICServiceError(Exception):
    """
    Base exception for CPIC service errors.
    """
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class CPICConnectionError(CPICServiceError):
    """
    Raised when CPIC API connection fails.
    """
    pass


class CPICAPIError(CPICServiceError):
    """
    Raised when CPIC API returns an error response.
    """
    pass


class CPICDataNotFoundError(CPICServiceError):
    """
    Raised when no Level A/B recommendations found.
    """
    pass


# Data Models
class CPICRecommendation:
    """
    Structured CPIC recommendation from API response.
    """
    
    def __init__(
        self,
        drug_name: str,
        gene_symbol: str,
        phenotype: str,
        recommendation: str,
        classification: str,
        guideline_level: str,
        guideline_url: Optional[str] = None
    ):
        self.drug_name = drug_name
        self.gene_symbol = gene_symbol
        self.phenotype = phenotype
        self.recommendation = recommendation
        self.classification = classification
        self.guideline_level = guideline_level
        self.guideline_url = guideline_url or f"https://cpicpgx.org/guidelines/"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        """
        return {
            "drug_name": self.drug_name,
            "gene_symbol": self.gene_symbol,
            "phenotype": self.phenotype,
            "recommendation": self.recommendation,
            "classification": self.classification,
            "guideline_level": self.guideline_level,
            "guideline_url": self.guideline_url,
        }
    
    def __repr__(self) -> str:
        """
        String representation for debugging.
        """
        return (
            f"CPICRecommendation(drug='{self.drug_name}', "
            f"gene='{self.gene_symbol}', "
            f"phenotype='{self.phenotype}', "
            f"classification='{self.classification}', "
            f"level='{self.guideline_level}')"
        )


# CPICService Class
class CPICService:
    """
    Asynchronous service for querying CPIC pharmacogenomic guidelines.
    """
    
    def __init__(self, base_url: str = CPIC_API_BASE_URL, timeout: float = CPIC_API_TIMEOUT):
        """
        Initialize CPICService.
        """
        self.base_url = base_url
        self.timeout = timeout
        self.recommendation_endpoint = f"{base_url}/recommendation"
        logger.info(f"CPICService initialized with base_url='{base_url}'")
    
    async def fetch_recommendations(
        self,
        gene: str,
        phenotype: str
    ) -> List[CPICRecommendation]:
        """
        Fetch CPIC recommendations for a gene-phenotype pair.
        """
        logger.info(
            f"Fetching CPIC recommendations for gene='{gene}', phenotype='{phenotype}'"
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Query CPIC API with gene and phenotype filters
                params = {
                    "genesymbol": gene,
                    "phenotype": phenotype
                }
                
                logger.debug(
                    f"Querying CPIC API: {self.recommendation_endpoint} "
                    f"with params={params}"
                )
                
                response = await client.get(
                    self.recommendation_endpoint,
                    params=params
                )
                
                # Check for HTTP errors — 429 is treated as a connection error
                # to trigger the local fallback guideline engine upstream.
                if response.status_code == 429:
                    logger.warning("CPIC API rate-limited (429) — triggering fallback")
                    raise CPICConnectionError(
                        message="CPIC API rate limit exceeded",
                        details="HTTP 429 Too Many Requests"
                    )
                if response.status_code != 200:
                    logger.error(
                        "CPIC API returned status %s", response.status_code
                    )
                    raise CPICAPIError(
                        message=f"CPIC API error: HTTP {response.status_code}",
                        details="Upstream error"
                    )
                
                # Parse JSON response
                data = response.json()
                
                logger.debug(
                    f"CPIC API returned {len(data)} total recommendations"
                )
                
                # Filter and parse recommendations
                recommendations = self._parse_recommendations(
                    data,
                    gene,
                    phenotype
                )
                
                if not recommendations:
                    logger.warning(
                        f"No Level A/B recommendations found for "
                        f"gene='{gene}', phenotype='{phenotype}'"
                    )
                    raise CPICDataNotFoundError(
                        message=f"No Level A/B CPIC guidelines found",
                        details=f"Gene: {gene}, Phenotype: {phenotype}"
                    )
                
                logger.info(
                    f"Successfully retrieved {len(recommendations)} Level A/B "
                    f"recommendations for {gene}"
                )
                
                return recommendations
        
        except httpx.TimeoutException as e:
            logger.error(
                f"CPIC API request timeout after {self.timeout}s: {e}"
            )
            raise CPICConnectionError(
                message="CPIC API connection timeout",
                details=f"Timeout after {self.timeout} seconds"
            )
        
        except httpx.RequestError as e:
            logger.error(
                f"CPIC API connection error: {e}",
                exc_info=True
            )
            raise CPICConnectionError(
                message="Failed to connect to CPIC API",
                details=str(e)
            )
        
        except CPICServiceError:
            # Re-raise CPIC-specific errors
            raise
        
        except Exception as e:
            logger.error(
                f"Unexpected error fetching CPIC recommendations: {e}",
                exc_info=True
            )
            raise CPICServiceError(
                message="Unexpected error querying CPIC API",
                details=str(e)
            )
    
    def _parse_recommendations(
        self,
        data: List[Dict[str, Any]],
        gene: str,
        phenotype: str
    ) -> List[CPICRecommendation]:
        """
        Parse CPIC API response and filter for Level A/B recommendations.
        """
        recommendations: List[CPICRecommendation] = []
        
        for item in data:
            # Extract guideline information
            guideline = item.get("guideline", {})
            guideline_level = guideline.get("level", "").upper()
            
            # Filter only Level A or B recommendations
            if guideline_level not in ["A", "B"]:
                logger.debug(
                    f"Skipping recommendation with level '{guideline_level}' "
                    f"(not A or B)"
                )
                continue
            
            # Extract recommendation details
            drug_name = item.get("drugname", "Unknown")
            recommendation_text = item.get("recommendation", "")
            classification = item.get("classification", "Unspecified")
            
            # Extract guideline URL if available
            guideline_url = guideline.get("url") or guideline.get("guideline_url")
            
            # Create structured recommendation object
            recommendation = CPICRecommendation(
                drug_name=drug_name,
                gene_symbol=gene,
                phenotype=phenotype,
                recommendation=recommendation_text,
                classification=classification,
                guideline_level=guideline_level,
                guideline_url=guideline_url
            )
            
            recommendations.append(recommendation)
            
            logger.debug(
                f"Parsed Level {guideline_level} recommendation: "
                f"{drug_name} ({classification})"
            )
        
        return recommendations
    
    async def fetch_gene_substrates(self, gene: str) -> List[str]:
        """
        Fetch all drug names paired with a gene from the CPIC /pair endpoint.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/pair",
                    params={"genesymbol": gene}
                )

                if response.status_code != 200:
                    logger.warning(
                        f"CPIC /pair returned status {response.status_code} for {gene}"
                    )
                    return []

                pairs = response.json()
                if not isinstance(pairs, list):
                    return []

                # Deduplicate and lowercase; filter out empty/None names
                names = sorted({
                    item["drugname"].lower()
                    for item in pairs
                    if item.get("drugname")
                })

                logger.info(
                    f"Loaded {len(names)} CPIC substrate drugs for {gene}"
                )
                return names

        except Exception as e:
            logger.warning(f"Failed to fetch CPIC substrates for {gene}: {e}")
            return []

    async def check_api_health(self) -> bool:
        """
        Check if CPIC API is reachable.
        """
        try:
            async with httpx.AsyncClient(
                timeout=5.0,
                follow_redirects=True  # Allow 301 redirects
            ) as client:
                # Use the recommendation endpoint for health check to avoid 301
                health_url = f"{self.base_url}/recommendation"
                response = await client.get(health_url)
                is_healthy = response.status_code == 200
                
                logger.info(
                    f"CPIC API health check: "
                    f"{'HEALTHY' if is_healthy else 'UNHEALTHY'} "
                    f"(status={response.status_code})"
                )
                
                return is_healthy
        
        except Exception as e:
            logger.error(f"CPIC API health check failed: {e}")
            return False


# Factory Function
def create_cpic_service() -> CPICService:
    """
    Factory function to create a CPICService instance.
    """
    return CPICService()
