"""Tests for backend/app/api/dependencies.py — get_db and get_current_user.

Covers:
  - get_current_user: valid token → User, invalid/expired token → 401,
    missing user → 401, inactive user → 401.
  - get_db: re-export from app.core.database (identity check).
  - Integration: auth_service.decode_token + user_service.get_user_by_id wiring.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_current_user, get_db, require_role
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.services.auth_service import create_access_token


def _make_tenant(db_session) -> Tenant:
    """Create a minimal tenant for FK satisfaction."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Company s.r.o.",
        ico=f"{uuid.uuid4().int % 100000000:08d}",
        address_street="Test 1",
        address_city="Bratislava",
        address_zip="81101",
        address_country="SK",
        bank_iban="SK3112000000198742637541",
        schema_name=f"tenant_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


# ---------------------------------------------------------------------------
# get_db re-export
# ---------------------------------------------------------------------------


def test_get_db_is_reexported_from_core():
    """get_db in api.dependencies is the same object as core.database.get_db."""
    from app.core.database import get_db as core_get_db

    assert get_db is core_get_db


# ---------------------------------------------------------------------------
# get_current_user — valid token
# ---------------------------------------------------------------------------


def test_get_current_user_valid_token(db_session):
    """Valid JWT for an active user returns the User object."""
    tenant = _make_tenant(db_session)
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        username="testuser",
        email="test@example.com",
        password_hash="fakehash",
        role="accountant",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    token = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role="accountant",
    )

    result = get_current_user(token=token, db=db_session)
    assert result.id == user.id
    assert result.username == "testuser"


# ---------------------------------------------------------------------------
# get_current_user — invalid token
# ---------------------------------------------------------------------------


def test_get_current_user_invalid_token(db_session):
    """Invalid JWT string raises HTTPException 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="not-a-valid-jwt", db=db_session)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


def test_get_current_user_expired_token(db_session):
    """Expired JWT raises HTTPException 401."""
    with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", -1):
        token = create_access_token(
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            role="accountant",
        )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user — user not found
# ---------------------------------------------------------------------------


def test_get_current_user_user_not_found(db_session):
    """Valid JWT but user not in DB raises HTTPException 401."""
    nonexistent_id = uuid.uuid4()
    token = create_access_token(
        user_id=nonexistent_id,
        tenant_id=uuid.uuid4(),
        role="accountant",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user — inactive user
# ---------------------------------------------------------------------------


def test_get_current_user_inactive_user(db_session):
    """Valid JWT for an inactive user raises HTTPException 401."""
    tenant = _make_tenant(db_session)
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        username="inactive_user",
        email="inactive@example.com",
        password_hash="fakehash",
        role="accountant",
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    token = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role="accountant",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user — decode_token integration
# ---------------------------------------------------------------------------


def test_get_current_user_uses_decode_token_from_auth_service():
    """Verify get_current_user delegates to auth_service.decode_token."""
    mock_db = MagicMock()
    mock_db.get.return_value = None  # user not found

    fake_payload = TokenPayload(
        sub=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role="accountant",
        exp=9999999999,
    )

    with patch("app.api.dependencies.decode_token", return_value=fake_payload) as mock_decode:
        with pytest.raises(HTTPException):
            get_current_user(token="sometoken", db=mock_db)
        mock_decode.assert_called_once_with("sometoken")


def test_get_current_user_uses_get_user_by_id_from_user_service():
    """Verify get_current_user delegates to user_service.get_user_by_id."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    fake_payload = TokenPayload(
        sub=user_id,
        tenant_id=tenant_id,
        role="accountant",
        exp=9999999999,
    )
    fake_user = MagicMock(spec=User)
    fake_user.is_active = True

    with (
        patch("app.api.dependencies.decode_token", return_value=fake_payload),
        patch("app.api.dependencies.get_user_by_id", return_value=fake_user) as mock_get,
    ):
        result = get_current_user(token="sometoken", db=MagicMock())
        mock_get.assert_called_once()
        assert result is fake_user


# ---------------------------------------------------------------------------
# get_current_user — WWW-Authenticate header
# ---------------------------------------------------------------------------


def test_get_current_user_returns_www_authenticate_header(db_session):
    """401 response includes WWW-Authenticate: Bearer header."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="bad-token", db=db_session)
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


# ---------------------------------------------------------------------------
# require_role — RBAC enforcement
# ---------------------------------------------------------------------------


def test_require_role_allowed(db_session):
    """User with an allowed role passes the check and is returned."""
    tenant = _make_tenant(db_session)
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        username="director_user",
        email="director@example.com",
        password_hash="fakehash",
        role="director",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(user)
    db_session.flush()

    checker = require_role("director", "accountant")

    # Call the inner dependency directly, providing current_user
    result = checker(current_user=user)
    assert result is user


def test_require_role_forbidden():
    """User with a disallowed role raises HTTPException 403."""
    fake_user = MagicMock(spec=User)
    fake_user.role = "employee"

    checker = require_role("director", "accountant")

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=fake_user)
    assert exc_info.value.status_code == 403
    assert "Insufficient permissions" in exc_info.value.detail


def test_require_role_single_role():
    """require_role works with a single allowed role."""
    fake_user = MagicMock(spec=User)
    fake_user.role = "director"

    checker = require_role("director")
    result = checker(current_user=fake_user)
    assert result is fake_user


def test_require_role_returns_callable():
    """require_role returns a callable (dependency function)."""
    checker = require_role("director")
    assert callable(checker)


def test_require_role_multiple_roles_all_accepted():
    """Each allowed role passes the check."""
    for role in ("director", "accountant", "employee"):
        fake_user = MagicMock(spec=User)
        fake_user.role = role

        checker = require_role("director", "accountant", "employee")
        result = checker(current_user=fake_user)
        assert result is fake_user
