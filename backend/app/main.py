"""
FastAPI application entry point for Pharmaco Navigator.
Implements SMART on FHIR authentication with BFF pattern and secure session management.
"""

import logging
import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.db.session import engine
from app.api.v1 import auth, fhir, alerts, patient
from app.models.schemas import HealthCheckResponse
# Import all SQLModel table classes
from app.models.genotype import Genotype
from app.services.genomic_service import GenomicConnectionError, GenomicDataNotFoundError
from app.services.cpic_service import CPICConnectionError, CPICAPIError

logger = logging.getLogger("pharmaco.navigator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager to handle startup and shutdown events.
    """

    # Startup
    # Audit file handler - writes to the HIPAA-compliant volume mount.
    # Falls back to stderr with an explicit warning if the path is unavailable
    _audit_log_path = "/var/log/pharmaco_audit/audit.log"
    _audit_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    try:
        _file_handler = logging.FileHandler(_audit_log_path, encoding="utf-8")
        _file_handler.setLevel(logging.INFO)
        _file_handler.setFormatter(_audit_formatter)
        logger.addHandler(_file_handler)
        logger.info("Audit file handler attached — writing to %s", _audit_log_path)
    except OSError as _ose:
        _stream_handler = logging.StreamHandler(sys.stderr)
        _stream_handler.setLevel(logging.INFO)
        _stream_handler.setFormatter(_audit_formatter)
        logger.addHandler(_stream_handler)
        logger.warning(
            "Audit volume unavailable (%s). "
            "Falling back to stderr stream logging.",
            _ose,
        )

    logger.info("Starting %s (environment: %s)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    logger.info("FHIR base URL: %s", settings.CERNER_FHIR_BASE_URL)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database schema initialised — all tables verified / created.")
    except SQLAlchemyError as exc:
        logger.error(
            "Database schema initialisation failed (SQLAlchemy): %s",
            exc,
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error during database schema initialisation: %s",
            exc,
            exc_info=True,
        )
        raise

    yield

    # Shutdown
    logger.info("Shutting down %s — disposing connection pool.", settings.PROJECT_NAME)
    await engine.dispose()


# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "An Automated Clinical Decision Support System "
        "for Genomic-Informed Medication Safety"
    ),
    version="1.0.0",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan
)

# Configure CORS for EHR integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# SessionMiddleware for secure session management
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie=settings.SESSION_COOKIE_NAME,
    max_age=settings.SESSION_MAX_AGE,
    same_site=settings.session_cookie_samesite,
    https_only=settings.session_cookie_secure, 
)


# Global Exception Handlers
@app.exception_handler(GenomicConnectionError)
async def genomic_connection_error_handler(
    request: Request, 
    exc: GenomicConnectionError
) -> JSONResponse:
    """
    Handle Azure PostgreSQL connection failures.
    """
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Genomic database is temporarily unavailable. Please try again later.",
            "error_type": "database_connection_error",
            "service": "Azure PostgreSQL"
        }
    )


@app.exception_handler(GenomicDataNotFoundError)
async def genomic_data_not_found_handler(
    request: Request, 
    exc: GenomicDataNotFoundError
) -> JSONResponse:
    """
    Handle missing patient genomic data.
    """
    return JSONResponse(
        status_code=404,
        content={
            "detail": "No genomic data found for this patient. Genomic testing may not have been ordered.",
            "error_type": "genomic_data_not_found",
            "recommendation": "Order pharmacogenomic panel testing for this patient"
        }
    )


@app.exception_handler(CPICConnectionError)
async def cpic_connection_error_handler(
    request: Request, 
    exc: CPICConnectionError
) -> JSONResponse:
    """
    Handle CPIC API connection failures.
    """
    return JSONResponse(
        status_code=503,
        content={
            "detail": "CPIC API is temporarily unavailable. Using local fallback guidelines.",
            "error_type": "cpic_api_connection_error",
            "service": "CPIC Pharmacogenomics API",
            "fallback_status": "active"
        }
    )


@app.exception_handler(CPICAPIError)
async def cpic_api_error_handler(
    request: Request, 
    exc: CPICAPIError
) -> JSONResponse:
    """
    Handle CPIC API errors.
    """
    return JSONResponse(
        status_code=503,
        content={
            "detail": "CPIC API returned an error. Using local fallback guidelines.",
            "error_type": "cpic_api_error",
            "service": "CPIC Pharmacogenomics API",
            "fallback_status": "active"
        }
    )


# Include API Routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)
app.include_router(
    fhir.router,
    prefix=f"{settings.API_V1_PREFIX}/fhir",
    tags=["FHIR Resources"]
)
app.include_router(
    alerts.router,
    prefix=f"{settings.API_V1_PREFIX}/alerts",
    tags=["Clinical Alerts"]
)
app.include_router(
    patient.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["Patient Clinical Insights"]
)


@app.get("/", tags=["Health"])
async def root() -> HealthCheckResponse:
    """
    Root endpoint for health check.
    """
    return HealthCheckResponse(
        status="healthy",
        application=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="1.0.0"
    )


@app.get("/api/health", tags=["Health"])
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint for monitoring and load balancers.
    """
    return HealthCheckResponse(
        status="ok",
        service="pharmaco-navigator-api",
        fhirEnabled=True
    )
