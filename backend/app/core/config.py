"""
Application configuration using Pydantic Settings.
Loads environment variables for SMART on FHIR authentication and secure session management.
"""

from pathlib import Path
from typing import List, Literal
from urllib.parse import urlparse
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve .env relative to this file (backend/.env)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Supports SMART on FHIR Provider EHR Launch with OAuth 2.0.
    """
    
    # SMART on FHIR Configuration
    CERNER_CLIENT_ID: str
    CERNER_CLIENT_SECRET: str
    CERNER_REDIRECT_URI: str
    CERNER_AUTHORIZATION_URL: str = (
        "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/"
        "protocols/oauth2/profiles/smart-v1/personas/provider/authorize"
    )
    CERNER_TOKEN_URL: str = (
        "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d/"
        "protocols/oauth2/profiles/smart-v1/token"
    )
    CERNER_FHIR_BASE_URL: str = (
        "https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    )
    
    # Security Configuration (HIPAA-compliant)
    SECRET_KEY: str
    SESSION_COOKIE_NAME: str = "pharmaco_session"
    SESSION_MAX_AGE: int = 3600  # 1 hour session timeout
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/pharmaco_navigator"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Pharmaco Navigator"
    ENVIRONMENT: str = "development"
    
    # External APIs
    RXNAV_API_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    CPIC_API_BASE_URL: str = "https://api.cpicpgx.org/v1"
    
    # CORS Configuration
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000"

    # Frontend base URL used for post-auth redirects
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    @field_validator("FRONTEND_BASE_URL")
    @classmethod
    def validate_frontend_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("FRONTEND_BASE_URL must be a valid http:// or https:// URL with a host")
        return v.rstrip("/")

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Validate SECRET_KEY meets minimum security requirements.
        """
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters for secure session management"
            )
        return v
    
    @field_validator("CERNER_CLIENT_ID")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """
        Ensure CERNER_CLIENT_ID is configured.
        """
        if not v or v == "your_cerner_client_id_here":
            raise ValueError(
                "CERNER_CLIENT_ID must be configured with valid credentials from Cerner"
            )
        return v
    
    def get_allowed_origins_list(self) -> List[str]:
        """
        Parse ALLOWED_ORIGINS string into a list for CORS middleware.
        """
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def is_production(self) -> bool:
        """
        Check if running in production environment.
        """
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def session_cookie_secure(self) -> bool:
        """
        Enable secure cookies in production.
        """
        return self.is_production
    
    @property
    def session_cookie_samesite(self) -> Literal["lax", "strict", "none"]:
        """
        Set SameSite policy for SMART on FHIR launches.
        """
        return "lax"
    
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings() # type: ignore[call-arg]
