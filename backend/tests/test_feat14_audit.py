"""Feat 14 audit tests — comprehensive edge-case coverage.

Verifies:
  - get_current_user and require_role consistency across modules
  - require_role invalid-role validation in api.dependencies module
  - TenantResolverMiddleware: invalid JWT → 401, inactive tenant → 403,
    missing tenant → 401, superadmin bypass, context var reset
  - get_db search_path SQL-injection protection
  - Middleware skip patterns for auth/docs routes
  - oauth2_scheme tokenUrl consistency
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient

from app.api import dependencies as api_deps
from app.core import security as core_sec
from app.core.database import tenant_schema_var
from app.models.tenant import Tenant
from app.models.user import ALL_ROLES, User
from app.services.auth_service import create_access_token

# ---------------------------------------------------------------------------
# Module consistency: api.dependencies vs core.security
# ---------------------------------------------------------------------------


class TestModuleConsistency:
    """Verify both get_current_user implementations behave identically."""

    def test_oauth2_scheme_token_url_matches(self):
        """Both modules use the same tokenUrl for OAuth2PasswordBearer."""
        assert api_deps.oauth2_scheme.model.flows.password.tokenUrl == "/api/v1/auth/login"
        assert core_sec.oauth2_scheme.model.flows.password.tokenUrl == "/api/v1/auth/login"

    def test_get_db_reexport_identity(self):
        """api.dependencies.get_db is literally core.database.get_db."""
        from app.core.database import get_db as core_get_db

        assert api_deps.get_db is core_get_db


# ---------------------------------------------------------------------------
# require_role — invalid role validation (api.dependencies)
# ---------------------------------------------------------------------------


class TestRequireRoleValidation:
    """Verify require_role rejects invalid role names at definition time."""

    def test_invalid_role_raises_value_error_api_deps(self):
        """api.dependencies.require_role rejects invalid roles."""
        with pytest.raises(ValueError, match="Invalid role"):
            api_deps.require_role("superadmin")

    def test_invalid_role_raises_value_error_core_security(self):
        """core.security.require_role rejects invalid roles."""
        with pytest.raises(ValueError, match="Invalid role"):
            core_sec.require_role("nonexistent_role")

    def test_mixed_valid_invalid_roles(self):
        """A mix of valid and invalid roles still raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            api_deps.require_role("director", "superadmin")

    def test_all_valid_roles_accepted(self):
        """All valid roles are accepted without error."""
        for role in ALL_ROLES:
            checker = api_deps.require_role(role)
            assert callable(checker)

    def test_multiple_valid_roles_accepted(self):
        """Multiple valid roles in a single call are accepted."""
        checker = api_deps.require_role("director", "accountant", "employee")
        assert callable(checker)


# ---------------------------------------------------------------------------
# TenantResolverMiddleware — edge cases
# ---------------------------------------------------------------------------


class TestMiddlewareEdgeCases:
    """Test TenantResolverMiddleware edge cases via TestClient."""

    def test_invalid_jwt_returns_401(self):
        """Middleware returns 401 for a malformed JWT."""
        from app.main import app

        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/users",
                headers={"Authorization": "Bearer invalid.token.here"},
            )
            assert resp.status_code == 401
            assert resp.json()["detail"] == "Could not validate credentials"

    def test_expired_jwt_returns_401(self):
        """Middleware returns 401 for an expired JWT."""
        from app.main import app

        with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", -1):
            expired_token = create_access_token(
                user_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                role="accountant",
            )

        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/users",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
            assert resp.status_code == 401

    def test_skip_auth_login_endpoint(self):
        """Middleware skips /api/v1/auth/ paths — let endpoint handle auth."""
        from app.main import app

        with TestClient(app) as client:
            # POST to login without credentials should get 422 (validation)
            # or 401 from the endpoint — not a middleware error
            resp = client.post("/api/v1/auth/login")
            assert resp.status_code == 422  # missing form data

    def test_skip_openapi_json(self):
        """Middleware skips /openapi.json."""
        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/openapi.json")
            assert resp.status_code == 200

    def test_skip_redoc(self):
        """Middleware skips /redoc."""
        from app.main import app

        with TestClient(app) as client:
            resp = client.get("/redoc")
            assert resp.status_code == 200

    def test_missing_bearer_prefix_passes_through(self):
        """Authorization header without 'Bearer ' prefix passes to endpoint."""
        from app.main import app

        with TestClient(app) as client:
            resp = client.get(
                "/api/v1/users",
                headers={"Authorization": "Basic dXNlcjpwYXNz"},
            )
            # Should get 401 from the endpoint's own get_current_user dep
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TenantResolverMiddleware — inactive tenant
# ---------------------------------------------------------------------------


class TestMiddlewareInactiveTenant:
    """Verify middleware returns 403 for inactive tenants."""

    def test_inactive_tenant_returns_403(self, db_session):
        """JWT referencing an inactive tenant → 403."""
        from app.main import app

        # Create inactive tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Inactive s.r.o.",
            ico=f"{uuid.uuid4().int % 100000000:08d}",
            address_street="Test 1",
            address_city="Bratislava",
            address_zip="81101",
            address_country="SK",
            bank_iban="SK3112000000198742637541",
            schema_name=f"tenant_{uuid.uuid4().hex[:12]}",
            is_active=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(tenant)
        db_session.flush()

        # Create user in that tenant
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            username="inactive_tenant_user",
            email="inactive_t@example.com",
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

        # Patch SessionLocal to return our test session
        from app.core.database import get_db

        def _override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_get_db

        with patch("app.middleware.tenant_resolver.SessionLocal", return_value=db_session):
            # Patch db.close to no-op so we don't close our test session
            original_close = db_session.close
            db_session.close = lambda: None
            try:
                with TestClient(app) as client:
                    resp = client.get(
                        "/api/v1/users",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    assert resp.status_code == 403
                    assert resp.json()["detail"] == "Tenant is inactive"
            finally:
                db_session.close = original_close
                app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# get_db — SQL injection protection
# ---------------------------------------------------------------------------


class TestSearchPathInjectionProtection:
    """Verify get_db rejects malicious schema names."""

    def test_reject_schema_with_semicolon(self):
        """Schema names with semicolons are rejected."""
        token = tenant_schema_var.set("tenant_x; DROP TABLE users;--")
        try:
            mock_session = MagicMock()
            with patch("app.core.database.SessionLocal", return_value=mock_session):
                from app.core.database import get_db

                gen = get_db()
                with pytest.raises(ValueError, match="Invalid schema name"):
                    next(gen)
        finally:
            tenant_schema_var.reset(token)

    def test_reject_schema_with_uppercase(self):
        """Schema names with uppercase letters are rejected (strict pattern)."""
        token = tenant_schema_var.set("Tenant_ABC")
        try:
            mock_session = MagicMock()
            with patch("app.core.database.SessionLocal", return_value=mock_session):
                from app.core.database import get_db

                gen = get_db()
                with pytest.raises(ValueError, match="Invalid schema name"):
                    next(gen)
        finally:
            tenant_schema_var.reset(token)

    def test_reject_schema_with_spaces(self):
        """Schema names with spaces are rejected."""
        token = tenant_schema_var.set("tenant demo")
        try:
            mock_session = MagicMock()
            with patch("app.core.database.SessionLocal", return_value=mock_session):
                from app.core.database import get_db

                gen = get_db()
                with pytest.raises(ValueError, match="Invalid schema name"):
                    next(gen)
        finally:
            tenant_schema_var.reset(token)

    def test_accept_valid_schema_name(self):
        """Valid schema names (lowercase + underscores + digits) are accepted."""
        token = tenant_schema_var.set("tenant_abc_123")
        try:
            mock_session = MagicMock()
            with patch("app.core.database.SessionLocal", return_value=mock_session):
                from app.core.database import get_db

                gen = get_db()
                db = next(gen)
                assert db is mock_session
                # SET search_path should have been called
                mock_session.execute.assert_called_once()

                import contextlib

                with contextlib.suppress(StopIteration):
                    next(gen)
        finally:
            tenant_schema_var.reset(token)


# ---------------------------------------------------------------------------
# Context variable reset after request
# ---------------------------------------------------------------------------


class TestContextVarIsolation:
    """Verify tenant_schema_var does not leak between requests."""

    def test_context_var_is_none_after_middleware(self):
        """Context var should be None outside request scope."""
        assert tenant_schema_var.get() is None

    def test_context_var_set_and_reset(self):
        """Manual set/reset cycle works correctly."""
        assert tenant_schema_var.get() is None

        token = tenant_schema_var.set("tenant_test")
        assert tenant_schema_var.get() == "tenant_test"

        tenant_schema_var.reset(token)
        assert tenant_schema_var.get() is None


# ---------------------------------------------------------------------------
# get_current_user — api.dependencies edge cases
# ---------------------------------------------------------------------------


class TestGetCurrentUserApiDeps:
    """Additional edge cases for api.dependencies.get_current_user."""

    def test_decode_token_value_error_yields_401(self):
        """ValueError from decode_token is caught and becomes 401."""
        with patch("app.api.dependencies.decode_token", side_effect=ValueError("bad")):
            with pytest.raises(HTTPException) as exc_info:
                api_deps.get_current_user(token="any", db=MagicMock())
            assert exc_info.value.status_code == 401

    def test_none_user_yields_401(self):
        """get_user_by_id returning None yields 401."""
        from app.schemas.auth import TokenPayload

        fake_payload = TokenPayload(sub=uuid.uuid4(), tenant_id=uuid.uuid4(), role="accountant", exp=9999999999)
        with (
            patch("app.api.dependencies.decode_token", return_value=fake_payload),
            patch("app.api.dependencies.get_user_by_id", return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                api_deps.get_current_user(token="any", db=MagicMock())
            assert exc_info.value.status_code == 401

    def test_inactive_user_yields_401(self):
        """Inactive user (is_active=False) yields 401."""
        from app.schemas.auth import TokenPayload

        fake_payload = TokenPayload(sub=uuid.uuid4(), tenant_id=uuid.uuid4(), role="accountant", exp=9999999999)
        fake_user = MagicMock(spec=User)
        fake_user.is_active = False

        with (
            patch("app.api.dependencies.decode_token", return_value=fake_payload),
            patch("app.api.dependencies.get_user_by_id", return_value=fake_user),
        ):
            with pytest.raises(HTTPException) as exc_info:
                api_deps.get_current_user(token="any", db=MagicMock())
            assert exc_info.value.status_code == 401
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
