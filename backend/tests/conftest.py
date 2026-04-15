"""Test configuration and fixtures.

Uses TEST_DATABASE_URL — NEVER the production DATABASE_URL.
Implements transaction-based test isolation per DESIGN.md §Test DB Isolation.

Key pattern:
  - connection.begin() starts outer transaction
  - Session(join_transaction_mode="create_savepoint") makes session.commit()
    flush but NOT commit the outer transaction
  - transaction.rollback() at teardown undoes everything
"""

import os
from collections.abc import Generator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Ensure encryption key is available for EncryptedString fields in tests.
# Must be set before any model module that uses EncryptedString is loaded.
if not os.environ.get("PAYROLL_ENCRYPTION_KEY") and not os.environ.get("FERNET_KEY"):
    os.environ["PAYROLL_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

# Import app.models to trigger all model registrations via app.models.__init__
# so that Base.metadata is fully populated for create_all/drop_all.
import app.models  # noqa: F401
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User

# ---------------------------------------------------------------------------
# Database URL resolution
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+pg8000://nex_payroll:changeme@localhost:9174/nex_payroll_test",
)

# Safety: never accidentally use production DB
_PROD_DATABASE_URL = os.environ.get("DATABASE_URL", "")
if _PROD_DATABASE_URL and TEST_DATABASE_URL == _PROD_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must differ from DATABASE_URL. Refusing to run tests against production database."
    )


def _ensure_test_database_exists() -> None:
    """Create test database if it does not exist (connects to default 'postgres' DB)."""
    parts = TEST_DATABASE_URL.rsplit("/", 1)
    if len(parts) != 2:
        return
    base_url = parts[0]
    db_name = parts[1]

    admin_url = f"{base_url}/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db"),
                {"db": db_name},
            )
            if not result.scalar():
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


# ---------------------------------------------------------------------------
# Engine (lazy — created only when DB fixtures are used)
# ---------------------------------------------------------------------------
_engine = None


def _get_engine():
    """Return test engine, creating it on first access."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        _ensure_test_database_exists()
        _engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    return _engine


# ---------------------------------------------------------------------------
# Session-scoped: create/drop all tables
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    """Create all tables before tests, drop after all tests complete.

    If the test database is unreachable (e.g. no Docker running),
    DB-dependent tests will fail individually but non-DB tests still run.
    """
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS shared"))
            conn.commit()
        # Drop first to remove any seed data left by Alembic migrations,
        # then recreate clean tables for test isolation.
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    except Exception:
        # DB not available — non-DB tests will still pass;
        # DB-dependent tests will fail when requesting db_session fixture
        yield
        return

    yield

    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Per-test: transactional session with SAVEPOINT isolation
# ---------------------------------------------------------------------------
@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Yield a transactional DB session that rolls back after each test.

    Uses join_transaction_mode='create_savepoint' so that session.commit()
    inside tested code flushes but does NOT commit the outer transaction.
    transaction.rollback() at the end undoes everything.
    """
    engine = _get_engine()
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient with DB override
# ---------------------------------------------------------------------------
@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with get_db and auth overridden for test isolation.

    - get_db → returns the transactional test session
    - get_current_user → returns a fake director User (most permissive role)

    Ensures all API tests use the same transactional session
    (and thus get automatic rollback isolation).
    """
    import uuid
    from datetime import UTC, datetime

    from app.core.database import get_db
    from app.core.security import get_current_user
    from app.main import app

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    # Create a lightweight mock user for auth — director role grants full access
    _now = datetime.now(UTC)
    _fake_user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        username="testadmin",
        email="testadmin@test.local",
        password_hash="not-a-real-hash",
        role="director",
        is_active=True,
        created_at=_now,
        updated_at=_now,
    )

    def _override_get_current_user() -> User:
        return _fake_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with only get_db overridden — NO auth override.

    Use this fixture in tests that need to exercise real JWT authentication
    (e.g. auth router tests for login/me endpoints).
    """
    from app.core.database import get_db
    from app.main import app

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helper: test tenant for JWT-based fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _auth_tenant(db_session: Session) -> Tenant:
    """Create a minimal test tenant for auth-based fixtures."""
    tenant = Tenant(
        name="Auth Test Tenant",
        ico="99999999",
        schema_name="tenant_auth_test",
        address_street="Test 1",
        address_city="Bratislava",
        address_zip="81101",
        address_country="SK",
        bank_iban="SK0000000000000000000001",
        is_active=True,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


# ---------------------------------------------------------------------------
# Journey-specific auth fixtures (real JWT via /api/v1/auth/login)
# ---------------------------------------------------------------------------


def _login_and_get_headers(test_client: TestClient, username: str, password: str) -> dict[str, str]:
    """POST to login endpoint and return Authorization header dict."""
    response = test_client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, f"Login failed for {username}: {response.status_code} {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def superadmin_headers(
    auth_client: TestClient,
    db_session: Session,
    _auth_tenant: Tenant,
) -> dict[str, str]:
    """JWT Authorization headers for a superadmin (director) user.

    Creates a superadmin user in the test DB, logs in via the real
    auth endpoint, and returns ``{"Authorization": "Bearer <token>"}``.
    Password sourced from PAYROLL_SUPERADMIN_PASSWORD env var (default: changeme).
    """
    from app.services.auth_service import hash_password

    password = os.environ.get("PAYROLL_SUPERADMIN_PASSWORD", "changeme")
    user = User(
        tenant_id=_auth_tenant.id,
        username="superadmin",
        email="superadmin@test.local",
        password_hash=hash_password(password),
        role="director",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    return _login_and_get_headers(auth_client, "superadmin", password)


@pytest.fixture()
def director_headers(
    auth_client: TestClient,
    db_session: Session,
    _auth_tenant: Tenant,
) -> dict[str, str]:
    """JWT Authorization headers for a tenant director user.

    Creates a director user in the test DB, logs in via the real
    auth endpoint, and returns ``{"Authorization": "Bearer <token>"}``.
    Password sourced from PAYROLL_ADMIN_PASSWORD env var (default: changeme).
    """
    from app.services.auth_service import hash_password

    password = os.environ.get("PAYROLL_ADMIN_PASSWORD", "changeme")
    user = User(
        tenant_id=_auth_tenant.id,
        username="test_director",
        email="director@test.local",
        password_hash=hash_password(password),
        role="director",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    return _login_and_get_headers(auth_client, "test_director", password)


@pytest.fixture()
def accountant_headers(
    auth_client: TestClient,
    test_accountant_user: dict,
) -> dict[str, str]:
    """JWT Authorization headers for an accountant user.

    Requires ``test_accountant_user`` fixture (Task 19.3) which creates
    the user via the API.  Logs in via the real auth endpoint.
    """
    return _login_and_get_headers(auth_client, test_accountant_user["username"], "Test1234!@#$")


@pytest.fixture()
def employee_headers(
    auth_client: TestClient,
    test_employee_user: dict,
) -> dict[str, str]:
    """JWT Authorization headers for an employee user.

    Requires ``test_employee_user`` fixture (Task 19.3) which creates
    the user via the API.  Logs in via the real auth endpoint.
    """
    return _login_and_get_headers(auth_client, test_employee_user["username"], "Test1234!@#$")


# ---------------------------------------------------------------------------
# Test tenant fixture (real API round-trip)
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_tenant(
    auth_client: TestClient,
    superadmin_headers: dict[str, str],
) -> Generator[dict, None, None]:
    """Create a realistic test tenant via the API and clean up after the test.

    Yields the tenant dict (JSON response body from POST /api/v1/tenants).
    Cleanup DELETEs the tenant even if the test fails (yield-based teardown).
    """
    tenant_payload = {
        "name": "Test Firma s.r.o.",
        "ico": "12345678",
        "dic": "2023456789",
        "address_street": "Hlavná 42",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK3112000000198742637541",
        "bank_bic": "TATRSKBX",
    }

    # Create tenant
    response = auth_client.post(
        "/api/v1/tenants",
        json=tenant_payload,
        headers=superadmin_headers,
    )
    assert response.status_code == 201, f"Failed to create test tenant: {response.status_code} {response.text}"
    tenant = response.json()

    yield tenant

    # Cleanup — deactivate/delete tenant (runs even if test fails)
    auth_client.delete(
        f"/api/v1/tenants/{tenant['id']}",
        headers=superadmin_headers,
    )


# ---------------------------------------------------------------------------
# Test employee fixture (API round-trip — dependency for test_employee_user)
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_employee(
    auth_client: TestClient,
    director_headers: dict[str, str],
    test_tenant: dict,
) -> dict:
    """Create a test employee via API for use in user fixtures.

    Creates a health insurer via API if needed, then creates the employee.
    Returns the employee dict (JSON response body).
    """
    # Ensure at least one health insurer exists via API
    hi_response = auth_client.get("/api/v1/health-insurers", headers=director_headers)
    assert hi_response.status_code == 200
    hi_data = hi_response.json()
    if hi_data["total"] > 0:
        hi_id = hi_data["items"][0]["id"]
    else:
        hi_create = auth_client.post(
            "/api/v1/health-insurers",
            json={
                "code": "25",
                "name": "VšZP",
                "iban": "SK8975000000000000000000",
            },
            headers=director_headers,
        )
        assert hi_create.status_code == 201, (
            f"Failed to create health insurer: {hi_create.status_code} {hi_create.text}"
        )
        hi_id = hi_create.json()["id"]

    payload = {
        "tenant_id": test_tenant["id"],
        "employee_number": "EMP001",
        "first_name": "Ján",
        "last_name": "Testovací",
        "birth_date": "1990-05-15",
        "birth_number": "9005150001",
        "gender": "M",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "health_insurer_id": hi_id,
        "tax_declaration_type": "standard",
        "hire_date": "2024-01-15",
    }

    response = auth_client.post(
        "/api/v1/employees",
        json=payload,
        headers=director_headers,
    )
    assert response.status_code == 201, f"Failed to create test employee: {response.status_code} {response.text}"
    return response.json()


# ---------------------------------------------------------------------------
# Test user fixtures (accountant + employee)
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_accountant_user(
    auth_client: TestClient,
    director_headers: dict[str, str],
    test_tenant: dict,
) -> dict:
    """Create a test accountant user via the API.

    POST /api/v1/users with role='accountant'.
    Returns the user dict (JSON response body).
    No cleanup needed — tenant deactivation handles it.
    """
    payload = {
        "tenant_id": test_tenant["id"],
        "username": "accountant_test",
        "email": "accountant@test.local",
        "password": "Test1234!@#$",
        "role": "accountant",
    }

    response = auth_client.post(
        "/api/v1/users",
        json=payload,
        headers=director_headers,
    )
    assert response.status_code == 201, f"Failed to create accountant user: {response.status_code} {response.text}"
    return response.json()


@pytest.fixture()
def test_employee_user(
    auth_client: TestClient,
    director_headers: dict[str, str],
    test_tenant: dict,
    test_employee: dict,
) -> dict:
    """Create a test employee user via the API.

    POST /api/v1/users with role='employee' linked to test_employee.
    Returns the user dict (JSON response body).
    No cleanup needed — tenant deactivation handles it.
    """
    payload = {
        "tenant_id": test_tenant["id"],
        "username": "employee_test",
        "email": "employee@test.local",
        "password": "Test1234!@#$",
        "role": "employee",
        "employee_id": test_employee["id"],
    }

    response = auth_client.post(
        "/api/v1/users",
        json=payload,
        headers=director_headers,
    )
    assert response.status_code == 201, f"Failed to create employee user: {response.status_code} {response.text}"
    return response.json()
