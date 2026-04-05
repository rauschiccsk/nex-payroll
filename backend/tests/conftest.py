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
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Import Base and all models so metadata is fully populated
from app.models import Base  # noqa: F401
from app.models.contribution_rate import ContributionRate  # noqa: F401
from app.models.health_insurer import HealthInsurer  # noqa: F401
from app.models.statutory_deadline import StatutoryDeadline  # noqa: F401
from app.models.tax_bracket import TaxBracket  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401

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
    """FastAPI TestClient with get_db overridden to use test session.

    Ensures all API tests use the same transactional session
    (and thus get automatic rollback isolation).
    """
    from app.core.database import get_db
    from app.main import app

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
