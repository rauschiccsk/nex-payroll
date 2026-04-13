"""Tests for Auth router.

Covers:
  POST /api/v1/auth/login  — OAuth2 password flow
  GET  /api/v1/auth/me     — current user info

DESIGN.md §2.3.1 + §6.1
"""

from datetime import UTC

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user import create_user

LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session: Session, **overrides) -> Tenant:
    defaults = {
        "name": "Auth Test s.r.o.",
        "ico": "77777777",
        "address_street": "Testova 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "schema_name": "tenant_auth_test_77777777",
    }
    defaults.update(overrides)
    t = Tenant(**defaults)
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def test_user(db_session: Session) -> tuple[User, str]:
    """Create a test user and return (user, plaintext_password)."""
    tenant = _make_tenant(db_session)
    plaintext = "TestPass123!"
    payload = UserCreate(
        tenant_id=tenant.id,
        username="testuser",
        email="testuser@example.com",
        password=plaintext,
        role="accountant",
    )
    user = create_user(db_session, payload)
    db_session.flush()
    return user, plaintext


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    """Tests for the login endpoint."""

    def test_login_success(self, client: TestClient, test_user):
        """Correct credentials → 200 with access_token."""
        user, password = test_user
        resp = client.post(
            LOGIN_URL,
            data={"username": user.username, "password": password},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Wrong password → 401."""
        user, _ = test_user
        resp = client.post(
            LOGIN_URL,
            data={"username": user.username, "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_unknown_username(self, client: TestClient):
        """Non-existent username → 401."""
        resp = client.post(
            LOGIN_URL,
            data={"username": "nobody", "password": "whatever123"},
        )
        assert resp.status_code == 401

    def test_login_inactive_user(self, client: TestClient, db_session: Session):
        """Inactive user cannot log in → 401."""
        tenant = _make_tenant(db_session, ico="66666661", schema_name="tenant_auth_inactive_66666661")
        payload = UserCreate(
            tenant_id=tenant.id,
            username="inactiveuser",
            email="inactive@example.com",
            password="TestPass123!",
            role="accountant",
        )
        user = create_user(db_session, payload)
        user.is_active = False
        db_session.flush()

        resp = client.post(
            LOGIN_URL,
            data={"username": "inactiveuser", "password": "TestPass123!"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    """Tests for the me endpoint."""

    def _get_token(self, client: TestClient, username: str, password: str) -> str:
        resp = client.post(LOGIN_URL, data={"username": username, "password": password})
        assert resp.status_code == 200
        return resp.json()["access_token"]

    def test_me_with_valid_token(self, client: TestClient, test_user):
        """Valid token → 200 with user data."""
        user, password = test_user
        token = self._get_token(client, user.username, password)

        resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(user.id)
        assert body["username"] == user.username
        assert body["email"] == user.email
        assert body["role"] == user.role
        assert "password_hash" not in body

    def test_me_without_token(self, client: TestClient):
        """No token → 401."""
        resp = client.get(ME_URL)
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client: TestClient):
        """Garbage token → 401."""
        resp = client.get(ME_URL, headers={"Authorization": "Bearer not.a.real.token"})
        assert resp.status_code == 401

    def test_me_with_expired_token(self, client: TestClient, test_user):
        """Manually crafted expired token → 401."""
        from datetime import datetime, timedelta

        from jose import jwt

        from app.core.config import settings

        user, _ = test_user
        # Create token with expiry in the past
        past = datetime.now(UTC) - timedelta(hours=1)
        payload = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
            "exp": past,
        }
        expired_token = jwt.encode(payload, settings.payroll_jwt_secret, algorithm="HS256")

        resp = client.get(ME_URL, headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401
