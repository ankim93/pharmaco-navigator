"""
Type-safe application configuration for Pharmaco Navigator.
All settings are loaded from environment variables / .env via Pydantic Settings v2.
"""

import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"

# Wire the root "pharmaco.navigator" logger to stderr for ERROR+ at import time.
# All modules in this package obtain a child logger via getLogger("pharmaco.navigator.*"),
# so this single handler covers the entire tree without touching the root logger.
_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setLevel(logging.ERROR)
_stderr_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logging.getLogger("pharmaco.navigator").addHandler(_stderr_handler)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/pharmaco_navigator"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # ------------------------------------------------------------------ #
    # Security                                                             #
    # ------------------------------------------------------------------ #
    SECRET_KEY: str
    SESSION_COOKIE_NAME: str = "pharmaco_session"
    SESSION_MAX_AGE: int = 3600  # 1-hour TTL (HIPAA session timeout)

    # ------------------------------------------------------------------ #
    # Cerner OAuth 2.0 / SMART on FHIR                                    #
    # ------------------------------------------------------------------ #
    CERNER_CLIENT_ID: str
    CERNER_CLIENT_SECRET: str
    CERNER_REDIRECT_URI: str
    CERNER_AUTHORIZATION_URL: str = (
        "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d"
        "/protocols/oauth2/profiles/smart-v1/personas/provider/authorize"
    )
    CERNER_TOKEN_URL: str = (
        "https://authorization.cerner.com/tenants/ec2458f2-1e24-41c8-b71b-0e701af7583d"
        "/protocols/oauth2/profiles/smart-v1/token"
    )
    CERNER_FHIR_BASE_URL: str = (
        "https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
    )

    # ------------------------------------------------------------------ #
    # Application                                                          #
    # ------------------------------------------------------------------ #
    PROJECT_NAME: str = "Pharmaco Navigator"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000"

    # External APIs
    RXNAV_API_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    CPIC_API_BASE_URL: str = "https://api.cpicpgx.org/v1"

    # ------------------------------------------------------------------ #
    # Validators                                                           #
    # ------------------------------------------------------------------ #

    @field_validator("DATABASE_URL")
    @classmethod
    def normalise_db_scheme(cls, v: str) -> str:
        """Ensure the asyncpg driver scheme is present."""
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def enforce_key_entropy(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters for HMAC security")
        return v

    @field_validator("CERNER_CLIENT_ID")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        if not v or v == "your_cerner_client_id_here":
            raise ValueError("CERNER_CLIENT_ID must be set to valid Cerner sandbox credentials")
        return v

    @field_validator("FRONTEND_BASE_URL")
    @classmethod
    def validate_frontend_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("FRONTEND_BASE_URL must be a valid http(s):// URL with a host")
        return v.rstrip("/")

    # ------------------------------------------------------------------ #
    # Computed properties                                                  #
    # ------------------------------------------------------------------ #

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def session_cookie_secure(self) -> bool:
        return self.is_production

    @property
    def session_cookie_samesite(self) -> Literal["lax", "strict", "none"]:
        return "lax"

    def get_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.
    Use as a FastAPI dependency: Depends(get_settings).
    """
    return Settings()  # type: ignore[call-arg]


# Module-level alias for backwards-compatible imports (e.g. `from app.core.config import settings`).
settings: Settings = get_settings()
