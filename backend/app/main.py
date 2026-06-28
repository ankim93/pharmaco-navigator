"""
FastAPI application entry point for Pharmaco Navigator.
Implements SMART on FHIR authentication with BFF pattern and secure session management.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1 import auth, fhir, alerts, patient
from app.models.schemas import HealthCheckResponse
from app.services.genomic_service import GenomicConnectionError, GenomicDataNotFoundError
from app.services.cpic_service import CPICConnectionError, CPICAPIError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager to handle startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.PROJECT_NAME}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"FHIR Base URL: {settings.CERNER_FHIR_BASE_URL}")
    yield
    # Shutdown
    print(f"Shutting down {settings.PROJECT_NAME}")


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
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=[],
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


class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware to avoid BaseHTTPMiddleware's cookie-dropping issue.
    """
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Content-Type-Options", "nosniff")
                headers.append("X-Frame-Options", "DENY")
                headers.append("Referrer-Policy", "strict-origin-when-cross-origin")
            await send(message)

        await self.app(scope, receive, send_with_security_headers)

app.add_middleware(SecurityHeadersMiddleware)


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
