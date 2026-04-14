"""Tests for require_role RBAC dependency and TenantResolverMiddleware.

Covers:
  - Role constants exported from app.models.user
  - require_role dependency: allowed / forbidden / invalid role
  - TenantResolverMiddleware: skip patterns, schema context var
  - get_db tenant-aware search_path via context variable
"""

import contextlib
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.security import get_current_user, require_role
from app.models.user import (
    ALL_ROLES,
    MANAGEMENT_ROLES,
    ROLE_ACCOUNTANT,
    ROLE_DIRECTOR,
    ROLE_EMPLOYEE,
    User,
)

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------


class TestRoleConstants:
    """Verify role constants are correct and consistent."""

    def test_role_values(self):
        assert ROLE_DIRECTOR == "director"
        assert ROLE_ACCOUNTANT == "accountant"
        assert ROLE_EMPLOYEE == "employee"

    def test_all_roles_tuple(self):
        assert set(ALL_ROLES) == {"director", "accountant", "employee"}
        assert len(ALL_ROLES) == 3

    def test_management_roles_subset(self):
        assert set(MANAGEMENT_ROLES) == {"director", "accountant"}
        assert set(MANAGEMENT_ROLES).issubset(set(ALL_ROLES))

    def test_employee_not_in_management(self):
        assert ROLE_EMPLOYEE not in MANAGEMENT_ROLES


# ---------------------------------------------------------------------------
# require_role dependency
# ---------------------------------------------------------------------------


def _make_fake_user(role: str) -> User:
    """Create a lightweight User object for testing."""
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        username="test",
        email="test@test.local",
        password_hash="fake-hash",
        role=role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


class TestRequireRole:
    """Test require_role dependency factory."""

    def test_director_allowed(self):
        """Director can access director-only endpoint."""
        app = FastAPI()

        @app.get("/admin", dependencies=[Depends(require_role(ROLE_DIRECTOR))])
        def admin_endpoint():
            return {"ok": True}

        fake_user = _make_fake_user(ROLE_DIRECTOR)
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with TestClient(app) as client:
            resp = client.get("/admin")
            assert resp.status_code == 200

    def test_accountant_forbidden_on_director_only(self):
        """Accountant cannot access director-only endpoint."""
        app = FastAPI()

        @app.get("/admin", dependencies=[Depends(require_role(ROLE_DIRECTOR))])
        def admin_endpoint():
            return {"ok": True}

        fake_user = _make_fake_user(ROLE_ACCOUNTANT)
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with TestClient(app) as client:
            resp = client.get("/admin")
            assert resp.status_code == 403
            assert "Insufficient permissions" in resp.json()["detail"]

    def test_employee_forbidden_on_management_only(self):
        """Employee cannot access management endpoint."""
        app = FastAPI()

        @app.get(
            "/manage",
            dependencies=[Depends(require_role(ROLE_DIRECTOR, ROLE_ACCOUNTANT))],
        )
        def manage_endpoint():
            return {"ok": True}

        fake_user = _make_fake_user(ROLE_EMPLOYEE)
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with TestClient(app) as client:
            resp = client.get("/manage")
            assert resp.status_code == 403

    def test_accountant_allowed_on_management(self):
        """Accountant can access management endpoint."""
        app = FastAPI()

        @app.get(
            "/manage",
            dependencies=[Depends(require_role(ROLE_DIRECTOR, ROLE_ACCOUNTANT))],
        )
        def manage_endpoint():
            return {"ok": True}

        fake_user = _make_fake_user(ROLE_ACCOUNTANT)
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with TestClient(app) as client:
            resp = client.get("/manage")
            assert resp.status_code == 200

    def test_invalid_role_raises_value_error(self):
        """Passing an invalid role name raises ValueError at definition time."""
        with pytest.raises(ValueError, match="Invalid role"):
            require_role("superadmin")

    def test_require_role_returns_user(self):
        """The dependency returns the authenticated user on success."""
        app = FastAPI()

        @app.get("/me")
        def me_endpoint(
            current_user: User = Depends(require_role(ROLE_DIRECTOR)),  # noqa: B008
        ):
            return {"username": current_user.username, "role": current_user.role}

        fake_user = _make_fake_user(ROLE_DIRECTOR)
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with TestClient(app) as client:
            resp = client.get("/me")
            assert resp.status_code == 200
            data = resp.json()
            assert data["username"] == "test"
            assert data["role"] == ROLE_DIRECTOR


# ---------------------------------------------------------------------------
# TenantResolverMiddleware
# ---------------------------------------------------------------------------


class TestTenantResolverMiddleware:
    """Test middleware skip patterns and context variable setting."""

    def test_skip_health_endpoint(self):
        """Middleware skips /health — no tenant resolution needed."""
        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "healthy"

    def test_skip_docs_endpoint(self):
        """Middleware skips /docs."""
        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/docs")
            # Docs page returns 200 (HTML)
            assert resp.status_code == 200

    def test_no_token_passes_through(self):
        """Request without Authorization header passes through to endpoint auth."""
        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/api/v1/users")
            # Should get 401 from get_current_user, not a middleware error
            assert resp.status_code == 401

    def test_context_var_default_is_none(self):
        """tenant_schema_var defaults to None when no middleware sets it."""
        from app.core.database import tenant_schema_var

        assert tenant_schema_var.get() is None


# ---------------------------------------------------------------------------
# get_db tenant-aware search_path
# ---------------------------------------------------------------------------


class TestGetDbTenantAware:
    """Test that get_db sets search_path when tenant_schema_var is set."""

    def test_no_schema_no_search_path(self):
        """When no tenant schema set, get_db does not issue SET search_path."""
        from app.core.database import tenant_schema_var

        # Ensure context var is clean
        assert tenant_schema_var.get() is None

        mock_session = MagicMock()
        with patch("app.core.database.SessionLocal", return_value=mock_session):
            from app.core.database import get_db

            gen = get_db()
            db = next(gen)
            assert db is mock_session
            # No execute call for SET search_path
            mock_session.execute.assert_not_called()
            with contextlib.suppress(StopIteration):
                next(gen)

    def test_with_schema_sets_search_path(self):
        """When tenant schema is set, get_db issues SET search_path."""
        from app.core.database import tenant_schema_var

        token = tenant_schema_var.set("tenant_demo")
        try:
            mock_session = MagicMock()
            with patch("app.core.database.SessionLocal", return_value=mock_session):
                from app.core.database import get_db

                gen = get_db()
                db = next(gen)
                assert db is mock_session

                # First call should be SET search_path
                calls = mock_session.execute.call_args_list
                assert len(calls) == 1
                sql_text = str(calls[0][0][0])
                assert "search_path" in sql_text
                assert "tenant_demo" in sql_text

                # Cleanup (triggers finally block)
                with contextlib.suppress(StopIteration):
                    next(gen)

                # After cleanup, reset search_path should have been called
                reset_calls = [c for c in mock_session.execute.call_args_list if "public" in str(c[0][0])]
                assert len(reset_calls) >= 1
        finally:
            tenant_schema_var.reset(token)
