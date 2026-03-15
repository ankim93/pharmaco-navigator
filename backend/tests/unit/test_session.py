"""Unit tests for app/core/session.py.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException


# Helper: build a minimal fake FastAPI Request with a controllable session
def _make_request(session: dict) -> MagicMock:
    req = MagicMock()
    req.session = session
    return req


# TestGetSessionValue
@pytest.mark.unit
class TestGetSessionValue:

    def test_returns_stored_value(self):
        from app.core.session import get_session_value
        req = _make_request({"key": "hello"})
        assert get_session_value(req, "key") == "hello"

    def test_returns_default_when_missing(self):
        from app.core.session import get_session_value
        req = _make_request({})
        assert get_session_value(req, "missing", default="fallback") == "fallback"

    def test_returns_none_default_when_not_provided(self):
        from app.core.session import get_session_value
        req = _make_request({})
        assert get_session_value(req, "missing") is None


# TestGetSessionString
@pytest.mark.unit
class TestGetSessionString:

    @pytest.mark.parametrize("stored,expected", [
        ("hello", "hello"),
        ("",      ""),
    ])
    def test_returns_string_values(self, stored, expected):
        from app.core.session import get_session_string
        req = _make_request({"k": stored})
        assert get_session_string(req, "k") == expected

    def test_missing_key_returns_default(self):
        from app.core.session import get_session_string
        req = _make_request({})
        assert get_session_string(req, "absent", default="DEF") == "DEF"

    def test_wrong_type_returns_default(self):
        """If the stored value is not a str (e.g. an int), return the default."""
        from app.core.session import get_session_string
        req = _make_request({"token": 12345})
        assert get_session_string(req, "token", default="fallback") == "fallback"


# TestGetSessionBool
@pytest.mark.unit
class TestGetSessionBool:

    @pytest.mark.parametrize("stored,expected", [
        (True,  True),
        (False, False),
    ])
    def test_returns_bool_values(self, stored, expected):
        from app.core.session import get_session_bool
        req = _make_request({"flag": stored})
        assert get_session_bool(req, "flag") == expected

    def test_missing_key_returns_false_default(self):
        from app.core.session import get_session_bool
        req = _make_request({})
        assert get_session_bool(req, "absent") is False

    def test_wrong_type_returns_default(self):
        """A truthy string stored where a bool is expected must return the default."""
        from app.core.session import get_session_bool
        req = _make_request({"authenticated": "true"})
        assert get_session_bool(req, "authenticated", default=False) is False


# TestGetSessionInt
@pytest.mark.unit
class TestGetSessionInt:

    def test_returns_int_value(self):
        from app.core.session import get_session_int
        req = _make_request({"count": 42})
        assert get_session_int(req, "count") == 42

    def test_missing_key_returns_0_default(self):
        from app.core.session import get_session_int
        req = _make_request({})
        assert get_session_int(req, "absent") == 0

    def test_wrong_type_returns_default(self):
        from app.core.session import get_session_int
        req = _make_request({"count": "not-an-int"})
        assert get_session_int(req, "count", default=99) == 99


# TestRequireAuthentication
@pytest.mark.unit
class TestRequireAuthentication:

    def test_passes_when_authenticated_is_true(self):
        from app.core.session import require_authentication
        req = _make_request({"authenticated": True})
        require_authentication(req)  # must not raise

    def test_raises_401_when_not_authenticated(self):
        from app.core.session import require_authentication
        req = _make_request({"authenticated": False})
        with pytest.raises(HTTPException) as exc_info:
            require_authentication(req)
        assert exc_info.value.status_code == 401

    def test_raises_401_when_authenticated_key_missing(self):
        from app.core.session import require_authentication
        req = _make_request({})
        with pytest.raises(HTTPException) as exc_info:
            require_authentication(req)
        assert exc_info.value.status_code == 401

    def test_raises_401_when_authenticated_is_wrong_type(self):
        """A non-bool 'authenticated' value (e.g. the string 'true') must still
        reject the session — get_session_bool falls back to False."""
        from app.core.session import require_authentication
        req = _make_request({"authenticated": "true"})
        with pytest.raises(HTTPException) as exc_info:
            require_authentication(req)
        assert exc_info.value.status_code == 401


# TestGetAccessToken
@pytest.mark.unit
class TestGetAccessToken:

    def test_returns_token_when_authenticated(self):
        from app.core.session import get_access_token
        req = _make_request({"authenticated": True, "access_token": "tok-abc123"})
        assert get_access_token(req) == "tok-abc123"

    def test_raises_401_when_not_authenticated(self):
        from app.core.session import get_access_token
        req = _make_request({"authenticated": False, "access_token": "tok-abc123"})
        with pytest.raises(HTTPException) as exc_info:
            get_access_token(req)
        assert exc_info.value.status_code == 401

    def test_raises_401_when_token_is_empty_string(self):
        """
        Authenticated session with a blank token must still be rejected.
        """
        from app.core.session import get_access_token
        req = _make_request({"authenticated": True, "access_token": ""})
        with pytest.raises(HTTPException) as exc_info:
            get_access_token(req)
        assert exc_info.value.status_code == 401

    def test_raises_401_when_token_is_missing(self):
        from app.core.session import get_access_token
        req = _make_request({"authenticated": True})
        with pytest.raises(HTTPException) as exc_info:
            get_access_token(req)
        assert exc_info.value.status_code == 401


# TestGetPatientId
@pytest.mark.unit
class TestGetPatientId:

    def test_returns_patient_id_when_authenticated(self):
        from app.core.session import get_patient_id
        req = _make_request({"authenticated": True, "patient_id": "12724067"})
        assert get_patient_id(req) == "12724067"

    def test_raises_401_when_not_authenticated(self):
        from app.core.session import get_patient_id
        req = _make_request({"authenticated": False, "patient_id": "12724067"})
        with pytest.raises(HTTPException) as exc_info:
            get_patient_id(req)
        assert exc_info.value.status_code == 401

    def test_raises_403_when_patient_id_missing(self):
        """
        Authenticated but no patient context -> 403 Security Context Error.
        """
        from app.core.session import get_patient_id
        req = _make_request({"authenticated": True})
        with pytest.raises(HTTPException) as exc_info:
            get_patient_id(req)
        assert exc_info.value.status_code == 403

    def test_raises_403_when_patient_id_is_empty(self):
        from app.core.session import get_patient_id
        req = _make_request({"authenticated": True, "patient_id": ""})
        with pytest.raises(HTTPException) as exc_info:
            get_patient_id(req)
        assert exc_info.value.status_code == 403
