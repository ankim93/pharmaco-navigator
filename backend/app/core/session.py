"""
Session utilities for type-safe BFF pattern implementation.
Provides helpers to safely store and retrieve typed session data.
"""

from typing import Optional, Any
from fastapi import Request, HTTPException, status


def is_demo_patient_id(patient_id: str) -> bool:
    """
    Return True for synthetic demo patient IDs (DEMO001–DEMO007).
    Demo patients bypass live Cerner OAuth — the recommendation engine
    serves them via DemoFHIRService without an active session token.
    """
    return patient_id.upper().startswith("DEMO")


def get_session_value(request: Request, key: str, default: Optional[Any] = None) -> Any:
    """
    Safely retrieve a value from session storage
    """
    return request.session.get(key, default)


def get_session_string(request: Request, key: str, default: str = "") -> str:
    """
    Retrieve a string value from session with type narrowing.
    """
    value = request.session.get(key, default)
    if isinstance(value, str):
        return value
    return default


def get_session_bool(request: Request, key: str, default: bool = False) -> bool:
    """
    Retrieve a boolean value from session with type narrowing.
    """
    value = request.session.get(key, default)
    if isinstance(value, bool):
        return value
    return default


def get_session_int(request: Request, key: str, default: int = 0) -> int:
    """
    Retrieve an integer value from session with type narrowing.
    """
    value = request.session.get(key, default)
    if isinstance(value, int):
        return value
    return default


def require_authentication(request: Request) -> None:
    """
    Verify that the request has an authenticated session.
    """
    authenticated = get_session_bool(request, "authenticated", False)
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please authenticate via SMART on FHIR launch."
        )


def get_access_token(request: Request) -> str:
    """
    Retrieve access token from session.
    """
    require_authentication(request)
    
    access_token = get_session_string(request, "access_token", "")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing from session. Please re-authenticate."
        )
    
    return access_token


def get_patient_id(request: Request) -> str:
    """
    Retrieve patient ID from session.
    """
    require_authentication(request)
    
    patient_id = get_session_string(request, "patient_id", "")
    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Context Error: Patient ID missing from session. "
                   "Unable to access patient data without context."
        )
    
    return patient_id


def get_fhir_server_url(request: Request) -> str:
    """
    Retrieve FHIR server URL from session.
    """
    from app.core.config import settings
    
    require_authentication(request)
    return get_session_string(
        request,
        "fhir_server_url",
        settings.CERNER_FHIR_BASE_URL
    )


def store_session_data(request: Request, token_response: dict[str, Any]) -> None:
    """
    Store OAuth token response in session with type-safe handling.
    """
    from app.core.config import settings
    
    # Type-safe extraction with validation
    access_token = token_response.get("access_token")
    patient_id = token_response.get("patient")
    
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token not received from authorization server"
        )
    
    if not isinstance(patient_id, str) or not patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Context Error: Patient ID missing from token response. "
                   "Unable to establish clinical session without patient context."
        )
    
    # Retrieve FHIR server URL from session (stored during launch)
    fhir_server_url = get_session_string(
        request,
        "iss",
        settings.CERNER_FHIR_BASE_URL
    )
    
    # Store credentials and context in secure server-side session
    request.session["access_token"] = access_token
    request.session["patient_id"] = patient_id
    request.session["fhir_server_url"] = fhir_server_url
    request.session["authenticated"] = True
    request.session["token_type"] = token_response.get("token_type", "Bearer")
    request.session["scope"] = token_response.get("scope", "")
    
    # Store optional refresh token if provided
    refresh_token = token_response.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        request.session["refresh_token"] = refresh_token


def clear_session(request: Request) -> None:
    """
    Clear all session data.
    """
    request.session.clear()


def get_authorization_header(request: Request) -> dict[str, str]:
    """
    Build Authorization header for FHIR API calls.
    """
    access_token = get_access_token(request)
    token_type = get_session_string(request, "token_type", "Bearer")
    
    return {
        "Authorization": f"{token_type} {access_token}",
        "Accept": "application/fhir+json"
    }
