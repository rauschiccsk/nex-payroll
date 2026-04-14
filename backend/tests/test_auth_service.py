"""Unit tests for app.services.auth_service.

Covers:
  - hash_password / verify_password (Argon2 via pwdlib)
  - create_access_token (JWT HS256)
  - decode_token (JWT decoding + validation)
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestHashPassword:
    """Tests for hash_password."""

    def test_returns_argon2_hash(self):
        """hash_password returns an Argon2 hash string."""
        hashed = hash_password("secret123")
        assert hashed.startswith("$argon2")

    def test_different_passwords_produce_different_hashes(self):
        h1 = hash_password("password_a")
        h2 = hash_password("password_b")
        assert h1 != h2

    def test_same_password_produces_different_hashes(self):
        """Argon2 uses random salt → same input, different output."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


class TestVerifyPassword:
    """Tests for verify_password."""

    def test_correct_password_returns_true(self):
        hashed = hash_password("my_password")
        assert verify_password("my_password", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    """Tests for create_access_token."""

    def test_returns_valid_jwt(self):
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_access_token(user_id, tenant_id, "accountant")
        payload = jwt.decode(token, settings.payroll_jwt_secret, algorithms=[ALGORITHM])
        assert payload["sub"] == str(user_id)
        assert payload["tenant_id"] == str(tenant_id)
        assert payload["role"] == "accountant"
        assert "exp" in payload

    def test_tenant_id_none(self):
        """Token with tenant_id=None encodes None."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id, None, "director")
        payload = jwt.decode(token, settings.payroll_jwt_secret, algorithms=[ALGORITHM])
        assert payload["tenant_id"] is None

    def test_expiry_is_approximately_30_minutes(self):
        before = datetime.now(UTC)
        token = create_access_token(uuid.uuid4(), uuid.uuid4(), "employee")
        after = datetime.now(UTC)

        payload = jwt.decode(token, settings.payroll_jwt_secret, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)

        expected_min = before + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES - 1)
        expected_max = after + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES + 1)
        assert expected_min <= exp <= expected_max


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------


class TestDecodeToken:
    """Tests for decode_token."""

    def test_decode_valid_token(self):
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        token = create_access_token(user_id, tenant_id, "accountant")

        tp = decode_token(token)
        assert tp.sub == user_id
        assert tp.tenant_id == tenant_id
        assert tp.role == "accountant"
        assert tp.exp > 0

    def test_decode_token_without_tenant(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id, None, "director")

        tp = decode_token(token)
        assert tp.sub == user_id
        assert tp.tenant_id is None

    def test_invalid_token_raises_value_error(self):
        with pytest.raises(ValueError, match="Could not validate credentials"):
            decode_token("not.a.valid.token")

    def test_expired_token_raises_value_error(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "role": "employee",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.payroll_jwt_secret, algorithm=ALGORITHM)
        with pytest.raises(ValueError, match="Could not validate credentials"):
            decode_token(token)

    def test_missing_sub_raises_value_error(self):
        payload = {
            "tenant_id": str(uuid.uuid4()),
            "role": "employee",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.payroll_jwt_secret, algorithm=ALGORITHM)
        with pytest.raises(ValueError, match="Could not validate credentials"):
            decode_token(token)

    def test_missing_role_raises_value_error(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.payroll_jwt_secret, algorithm=ALGORITHM)
        with pytest.raises(ValueError, match="Could not validate credentials"):
            decode_token(token)

    def test_invalid_sub_uuid_raises_value_error(self):
        payload = {
            "sub": "not-a-uuid",
            "tenant_id": str(uuid.uuid4()),
            "role": "employee",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.payroll_jwt_secret, algorithm=ALGORITHM)
        with pytest.raises(ValueError, match="Could not validate credentials"):
            decode_token(token)

    def test_invalid_tenant_id_uuid_raises_value_error(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "tenant_id": "not-a-uuid",
            "role": "employee",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.payroll_jwt_secret, algorithm=ALGORITHM)
        with pytest.raises(ValueError, match="Could not validate credentials"):
            decode_token(token)

    def test_wrong_secret_raises_value_error(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "role": "employee",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)
        with pytest.raises(ValueError, match="Could not validate credentials"):
            decode_token(token)
