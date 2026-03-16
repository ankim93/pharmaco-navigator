"""
API router tests for /api/v1/auth endpoints.
"""

from urllib.parse import parse_qs, urlparse
import httpx
import pytest
import respx
from httpx import AsyncClient
from app.core.config import settings


# Cerner sandbox FHIR ISS and a fake launch token
ISS = "https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"
LAUNCH_TOKEN = "TEST_LAUNCH_TOKEN"
PATIENT_ID = "12724067"

# Minimal valid Cerner token response
_MOCK_TOKEN = {
    "access_token": "ey.mock.access.token",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "launch openid fhirUser patient/Patient.read patient/MedicationRequest.read",
    "patient": PATIENT_ID,
}


def _extract_state(launch_response: httpx.Response) -> str:
    """Return the CSRF state value from a /launch redirect Location header."""
    location = launch_response.headers["location"]
    return parse_qs(urlparse(location).query)["state"][0]


# GET /auth/launch
@pytest.mark.unit
async def test_launch_returns_302_redirect_to_cerner(async_client: AsyncClient) -> None:
    """
    Launch endpoint must redirect the browser to the Cerner authorization server.
    """
    response = await async_client.get(
        "/api/v1/auth/launch",
        params={"iss": ISS, "launch": LAUNCH_TOKEN},
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)  # Starlette RedirectResponse defaults to 307
    assert settings.CERNER_AUTHORIZATION_URL in response.headers["location"]


@pytest.mark.unit
async def test_launch_redirect_url_contains_required_oauth_params(
    async_client: AsyncClient,
) -> None:
    """
    The redirect URL must carry client_id, redirect_uri, state, and SMART scopes.
    """
    response = await async_client.get(
        "/api/v1/auth/launch",
        params={"iss": ISS, "launch": LAUNCH_TOKEN},
        follow_redirects=False,
    )
    params = parse_qs(urlparse(response.headers["location"]).query)

    assert params["client_id"][0] == settings.CERNER_CLIENT_ID
    assert "state" in params             
    assert "redirect_uri" in params
    assert "launch" in params["scope"][0]


# GET /auth/callback
@pytest.mark.unit
async def test_callback_returns_401_when_oauth_error_param_present(
    async_client: AsyncClient,
) -> None:
    """
    Cerner sends back error=access_denied -> 401 Unauthorized.
    """
    response = await async_client.get(
        "/api/v1/auth/callback",
        params={"error": "access_denied", "error_description": "User denied access"},
    )
    assert response.status_code == 401
    assert "Authorization failed" in response.json()["detail"]


@pytest.mark.unit
async def test_callback_returns_400_when_state_not_in_session(
    async_client: AsyncClient,
) -> None:
    """
    State mismatch: no prior /launch call -> no oauth_state in session -> 400.
    """
    response = await async_client.get(
        "/api/v1/auth/callback",
        params={"code": "AUTH_CODE", "state": "forged-csrf-state"},
    )
    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


@pytest.mark.unit
async def test_callback_returns_400_when_code_missing_after_valid_launch(
    async_client: AsyncClient,
) -> None:
    """
    Valid CSRF state in cookie but no authorization code -> 400.
    """
    # Seed the session by going through /launch first
    launch_resp = await async_client.get(
        "/api/v1/auth/launch",
        params={"iss": ISS, "launch": LAUNCH_TOKEN},
        follow_redirects=False,
    )
    state = _extract_state(launch_resp)

    # Callback with correct state but missing code parameter
    response = await async_client.get(
        "/api/v1/auth/callback",
        params={"state": state},  
    )
    assert response.status_code == 400
    assert "code" in response.json()["detail"].lower()


@pytest.mark.unit
async def test_callback_success_redirects_to_frontend_dashboard(
    async_client: AsyncClient,
) -> None:
    """
    Full happy-path: valid launch -> valid callback with mocked token exchange
    -> 302 redirect to the React dashboard with the patient ID in the URL.
    """
    # /launch seeds oauth_state in the session cookie
    launch_resp = await async_client.get(
        "/api/v1/auth/launch",
        params={"iss": ISS, "launch": LAUNCH_TOKEN},
        follow_redirects=False,
    )
    state = _extract_state(launch_resp)

    # /callback with correct state + code; Cerner token exchange mocked
    with respx.mock:
        respx.post(settings.CERNER_TOKEN_URL).mock(
            return_value=httpx.Response(200, json=_MOCK_TOKEN)
        )
        response = await async_client.get(
            "/api/v1/auth/callback",
            params={"code": "AUTH_CODE_XYZ", "state": state},
            follow_redirects=False,
        )

    assert response.status_code == 302
    location = response.headers["location"]
    assert "dashboard" in location
    assert PATIENT_ID in location


@pytest.mark.unit
async def test_callback_returns_504_when_token_exchange_times_out(
    async_client: AsyncClient,
) -> None:
    """
    Cerner token endpoint unreachable (timeout) -> 504 Gateway Timeout.
    """
    launch_resp = await async_client.get(
        "/api/v1/auth/launch",
        params={"iss": ISS, "launch": LAUNCH_TOKEN},
        follow_redirects=False,
    )
    state = _extract_state(launch_resp)

    with respx.mock:
        respx.post(settings.CERNER_TOKEN_URL).mock(
            side_effect=httpx.TimeoutException("timed out")
        )
        response = await async_client.get(
            "/api/v1/auth/callback",
            params={"code": "AUTH_CODE_XYZ", "state": state},
        )

    assert response.status_code == 504


# POST /auth/logout
@pytest.mark.unit
async def test_logout_always_returns_logged_out(async_client: AsyncClient) -> None:
    """
    POST /logout succeeds regardless of session state and returns logged_out.
    """
    response = await async_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "logged_out"


# GET /auth/session
@pytest.mark.unit
async def test_session_returns_unauthenticated_with_no_prior_login(
    async_client: AsyncClient,
) -> None:
    """
    GET /session with no active session -> authenticated=False.
    """
    response = await async_client.get("/api/v1/auth/session")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is False
