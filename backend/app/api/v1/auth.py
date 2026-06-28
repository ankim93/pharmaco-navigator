"""
SMART on FHIR authentication endpoints.
Implements OAuth 2.0 authorization flow with BFF pattern for secure credential management.
"""

import hmac
import logging
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from typing import Optional
import secrets
import httpx
import base64
from urllib.parse import urlencode
from app.core.config import settings
from app.models.schemas import (
    CernerTokenResponse,
    SessionStatusResponse,
    LogoutResponse
)
from app.core.session import (
    store_session_data,
    clear_session,
    get_session_bool,
    get_session_string
)


router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/launch")
async def smart_launch(
    request: Request,
    iss: str,
    launch: str
) -> RedirectResponse:
    """
    SMART on FHIR EHR Launch endpoint.
    Initiates OAuth 2.0 authorization flow when launched from Cerner EHR.
    """
    # Generate state parameter for CSRF protection
    state: str = secrets.token_urlsafe(32)
    
    # Store state and launch context in session
    request.session["oauth_state"] = state
    request.session["launch_token"] = launch
    request.session["iss"] = iss
    
    # Build authorization URL with SMART scopes
    scopes: list[str] = [
        "launch",
        "openid",
        "fhirUser",
        "patient/Patient.read",
        "patient/MedicationRequest.read",
        "patient/Observation.read"
    ]
    
    auth_params: dict[str, str] = {
        "response_type": "code",
        "client_id": settings.CERNER_CLIENT_ID,
        "redirect_uri": settings.CERNER_REDIRECT_URI,
        "scope": " ".join(scopes),
        "state": state,
        "aud": iss,
        "launch": launch
    }
    
    # Construct authorization URL with proper encoding
    auth_url: str = f"{settings.CERNER_AUTHORIZATION_URL}?{urlencode(auth_params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
) -> RedirectResponse:
    """
    OAuth 2.0 callback endpoint.
    Receives authorization code from Cerner and exchanges it for access token.
    """
    # Handle authorization errors
    if error is not None:
        logger.warning("OAuth authorization error returned by identity provider: %s", error)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization failed. Please try again."
        )
    
    # Validate state parameter (CSRF protection).
    # hmac.compare_digest eliminates timing side-channels that a plain == comparison
    # leaks; an attacker measuring response latency cannot infer the correct token.
    stored_state: Optional[str] = get_session_string(request, "oauth_state", "")
    if not state or not stored_state or not hmac.compare_digest(
        state.encode(), stored_state.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter - possible CSRF attack"
        )
    
    # Validate authorization code is present
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code missing from callback"
        )
    
    # Exchange authorization code for access token
    token_data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.CERNER_REDIRECT_URI
    }
    
    # Create HTTP Basic Authorization header with client credentials (confidential client)
    credentials: str = f"{settings.CERNER_CLIENT_ID}:{settings.CERNER_CLIENT_SECRET}"
    encoded_credentials: str = base64.b64encode(credentials.encode()).decode()
    
    try:
        async with httpx.AsyncClient() as client:
            token_response: httpx.Response = await client.post(
                settings.CERNER_TOKEN_URL,
                data=token_data,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {encoded_credentials}"
                },
                timeout=10.0
            )
            
            # Check for successful token exchange
            if token_response.status_code != 200:
                logger.error(
                    "Token exchange failed: status=%s body=%s",
                    token_response.status_code,
                    token_response.text,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed. Please try again."
                )
            
            # Parse response with type-safe Pydantic model
            raw_json = token_response.json()
            token_data_response = CernerTokenResponse.model_validate(raw_json)
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Token exchange request timed out"
        )
    except httpx.RequestError as exc:
        logger.error("Failed to connect to Cerner authorization server: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again later."
        )
    
    # Store validated token response in session using type-safe helper
    # This validates access_token and patient_id are present
    store_session_data(request, token_data_response.model_dump())
    
    # Clear temporary OAuth state
    request.session.pop("oauth_state", None)
    request.session.pop("launch_token", None)
    
    # Redirect to frontend dashboard with patient ID for SMART launch context
    patient_id = token_data_response.patient
    return RedirectResponse(
        url=f"{settings.FRONTEND_BASE_URL}/dashboard?patient={patient_id}",
        status_code=status.HTTP_302_FOUND
    )


@router.post("/logout")
async def logout(request: Request) -> LogoutResponse:
    """
    Logout endpoint.
    Terminates session and purges all cached patient data.
    """
    # Clear all session data using type-safe helper
    clear_session(request)
    
    return LogoutResponse(
        status="logged_out",
        message="Session terminated and patient data purged"
    )


@router.get("/session")
async def get_session_status(request: Request) -> SessionStatusResponse:
    """
    Check current session authentication status.
    """
    authenticated: bool = get_session_bool(request, "authenticated", False)
    
    if not authenticated:
        return SessionStatusResponse(
            authenticated=False,
            message="No active session"
        )
    
    patient_id: str = get_session_string(request, "patient_id", "")
    
    return SessionStatusResponse(
        authenticated=True,
        patientId=patient_id if patient_id else None,
        expiresIn=settings.SESSION_MAX_AGE
    )