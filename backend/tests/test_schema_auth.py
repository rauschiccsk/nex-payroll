"""Tests for Auth Pydantic schemas (TokenPayload, Token, LoginRequest, LoginResponse, ChangePasswordRequest)."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    Token,
    TokenPayload,
)
from app.schemas.user import _PASSWORD_MIN_LENGTH

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = uuid4()
_TENANT_ID = uuid4()

# A password that satisfies complexity: uppercase, lowercase, digit, special, 12+ chars
_VALID_PASSWORD = "StrongPass1!xy"


# ---------------------------------------------------------------------------
# TokenPayload
# ---------------------------------------------------------------------------


class TestTokenPayload:
    """Tests for TokenPayload schema."""

    def test_valid_with_tenant(self):
        tp = TokenPayload(sub=_USER_ID, tenant_id=_TENANT_ID, role="accountant", exp=9999999999)
        assert tp.sub == _USER_ID
        assert tp.tenant_id == _TENANT_ID
        assert tp.role == "accountant"
        assert tp.exp == 9999999999

    def test_valid_without_tenant(self):
        tp = TokenPayload(sub=_USER_ID, role="director", exp=1234567890)
        assert tp.tenant_id is None

    def test_missing_sub_raises(self):
        with pytest.raises(ValidationError):
            TokenPayload(role="employee", exp=1234567890)

    def test_missing_role_raises(self):
        with pytest.raises(ValidationError):
            TokenPayload(sub=_USER_ID, exp=1234567890)

    def test_missing_exp_raises(self):
        with pytest.raises(ValidationError):
            TokenPayload(sub=_USER_ID, role="employee")

    def test_invalid_sub_uuid(self):
        with pytest.raises(ValidationError):
            TokenPayload(sub="not-a-uuid", role="employee", exp=123)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


class TestToken:
    """Tests for Token schema."""

    def test_valid(self):
        t = Token(access_token="eyJhbGciOiJIUzI1NiJ9.abc.def")
        assert t.access_token == "eyJhbGciOiJIUzI1NiJ9.abc.def"
        assert t.token_type == "bearer"

    def test_custom_token_type(self):
        t = Token(access_token="abc", token_type="mac")
        assert t.token_type == "mac"

    def test_missing_access_token_raises(self):
        with pytest.raises(ValidationError):
            Token()


# ---------------------------------------------------------------------------
# LoginRequest
# ---------------------------------------------------------------------------


class TestLoginRequest:
    """Tests for LoginRequest schema."""

    def test_valid(self):
        lr = LoginRequest(username="jnovak", password="secret")
        assert lr.username == "jnovak"
        assert lr.password == "secret"

    def test_missing_username_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="jnovak")


# ---------------------------------------------------------------------------
# LoginResponse
# ---------------------------------------------------------------------------


class TestLoginResponse:
    """Tests for LoginResponse schema."""

    def test_valid(self):
        user_data = {
            "id": _USER_ID,
            "username": "jnovak",
            "email": "jan@example.com",
            "role": "accountant",
            "is_active": True,
            "tenant_id": _TENANT_ID,
            "last_login_at": None,
        }
        lr = LoginResponse(access_token="tok123", user=user_data)
        assert lr.access_token == "tok123"
        assert lr.token_type == "bearer"
        assert lr.user.username == "jnovak"

    def test_inherits_token_type_default(self):
        user_data = {
            "id": _USER_ID,
            "username": "jnovak",
            "email": "jan@example.com",
            "role": "accountant",
            "is_active": True,
            "tenant_id": _TENANT_ID,
        }
        lr = LoginResponse(access_token="tok", user=user_data)
        assert lr.token_type == "bearer"

    def test_missing_user_raises(self):
        with pytest.raises(ValidationError):
            LoginResponse(access_token="tok123")


# ---------------------------------------------------------------------------
# ChangePasswordRequest
# ---------------------------------------------------------------------------


class TestChangePasswordRequest:
    """Tests for ChangePasswordRequest schema with password complexity."""

    def test_valid(self):
        cp = ChangePasswordRequest(old_password="oldpass", new_password=_VALID_PASSWORD)
        assert cp.old_password == "oldpass"
        assert cp.new_password == _VALID_PASSWORD

    def test_password_too_short(self):
        """Password shorter than _PASSWORD_MIN_LENGTH should fail."""
        short = "Ab1!" + "x" * (_PASSWORD_MIN_LENGTH - 5)  # exactly min - 1
        assert len(short) == _PASSWORD_MIN_LENGTH - 1
        with pytest.raises(ValidationError, match="at least"):
            ChangePasswordRequest(old_password="old", new_password=short)

    def test_password_min_length_matches_user_schema(self):
        """Ensure auth and user schemas share the same minimum length."""
        assert _PASSWORD_MIN_LENGTH == 12

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError, match="uppercase"):
            ChangePasswordRequest(old_password="old", new_password="nouppercase1!x")

    def test_password_no_lowercase(self):
        with pytest.raises(ValidationError, match="lowercase"):
            ChangePasswordRequest(old_password="old", new_password="NOLOWERCASE1!X")

    def test_password_no_digit(self):
        with pytest.raises(ValidationError, match="digit"):
            ChangePasswordRequest(old_password="old", new_password="NoDigitHere!xx")

    def test_password_no_special_char(self):
        with pytest.raises(ValidationError, match="special"):
            ChangePasswordRequest(old_password="old", new_password="NoSpecial1xxxx")

    def test_password_exactly_min_length_valid(self):
        """Password at exactly _PASSWORD_MIN_LENGTH with all criteria should pass."""
        pwd = "Aa1!" + "x" * (_PASSWORD_MIN_LENGTH - 4)
        assert len(pwd) == _PASSWORD_MIN_LENGTH
        cp = ChangePasswordRequest(old_password="old", new_password=pwd)
        assert cp.new_password == pwd
