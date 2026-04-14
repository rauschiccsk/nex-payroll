"""Tests for user_service (authenticate_user, get_user_by_id, create_user).

These test the high-level user service module (app.services.user_service)
that provides authentication and user management functions built on top of
the lower-level CRUD service (app.services.user) and auth primitives
(app.services.auth_service).
"""

from uuid import uuid4

import pytest

from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import hash_password
from app.services.user_service import authenticate_user, create_user, get_user_by_id

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session, **overrides) -> Tenant:
    """Insert a minimal Tenant and flush; return the instance."""
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "schema_name": "tenant_test_12345678",
    }
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _make_user(db_session, tenant, **overrides) -> User:
    """Insert a user with a hashed password directly via ORM."""
    defaults = {
        "tenant_id": tenant.id,
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": hash_password("SecurePass123!"),
        "role": "accountant",
        "is_active": True,
    }
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.flush()
    return user


def _make_payload(tenant_id, **overrides) -> UserCreate:
    """Build a valid UserCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "username": "jnovak",
        "email": "jan.novak@example.com",
        "password": "SecurePass123!",
        "role": "accountant",
        "is_active": True,
    }
    defaults.update(overrides)
    return UserCreate(**defaults)


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


class TestAuthenticateUser:
    """Tests for authenticate_user."""

    def test_authenticate_success(self, db_session):
        """Valid credentials return the User and update last_login_at."""
        tenant = _make_tenant(db_session)
        user = _make_user(db_session, tenant)

        result = authenticate_user(db_session, "testuser", "SecurePass123!")

        assert result is not None
        assert result.id == user.id
        assert result.last_login_at is not None

    def test_authenticate_wrong_password(self, db_session):
        """Wrong password returns None."""
        tenant = _make_tenant(db_session)
        _make_user(db_session, tenant)

        result = authenticate_user(db_session, "testuser", "WrongPass123!")

        assert result is None

    def test_authenticate_unknown_user(self, db_session):
        """Non-existent username returns None."""
        result = authenticate_user(db_session, "ghost", "SecurePass123!")
        assert result is None

    def test_authenticate_inactive_user(self, db_session):
        """Inactive user returns None."""
        tenant = _make_tenant(db_session)
        _make_user(db_session, tenant, is_active=False)

        result = authenticate_user(db_session, "testuser", "SecurePass123!")

        assert result is None

    def test_authenticate_updates_last_login(self, db_session):
        """Successful authentication updates last_login_at."""
        tenant = _make_tenant(db_session)
        user = _make_user(db_session, tenant)
        assert user.last_login_at is None

        result = authenticate_user(db_session, "testuser", "SecurePass123!")

        assert result is not None
        assert result.last_login_at is not None


# ---------------------------------------------------------------------------
# get_user_by_id
# ---------------------------------------------------------------------------


class TestGetUserById:
    """Tests for get_user_by_id."""

    def test_get_existing(self, db_session):
        tenant = _make_tenant(db_session)
        user = _make_user(db_session, tenant)

        result = get_user_by_id(db_session, user.id)

        assert result is not None
        assert result.id == user.id
        assert result.username == "testuser"

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_user_by_id(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


class TestCreateUser:
    """Tests for user_service.create_user."""

    def test_create_returns_model(self, db_session):
        tenant = _make_tenant(db_session)
        payload = _make_payload(tenant.id)

        result = create_user(db_session, payload)

        assert isinstance(result, User)
        assert result.id is not None
        assert result.username == "jnovak"
        assert result.email == "jan.novak@example.com"
        assert result.role == "accountant"
        # password_hash should NOT be the plaintext
        assert result.password_hash != "SecurePass123!"
        assert len(result.password_hash) > 20

    def test_create_duplicate_username_raises(self, db_session):
        tenant = _make_tenant(db_session)
        create_user(db_session, _make_payload(tenant.id))

        with pytest.raises(ValueError, match="already exists"):
            create_user(
                db_session,
                _make_payload(
                    tenant.id,
                    username="jnovak",
                    email="other@example.com",
                ),
            )

    def test_create_duplicate_email_raises(self, db_session):
        tenant = _make_tenant(db_session)
        create_user(db_session, _make_payload(tenant.id))

        with pytest.raises(ValueError, match="already exists"):
            create_user(
                db_session,
                _make_payload(
                    tenant.id,
                    username="other_user",
                    email="jan.novak@example.com",
                ),
            )
