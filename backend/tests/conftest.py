"""Pytest configuration and fixtures for NEX Payroll tests.

This module provides:
- SAVEPOINT-isolated test transactions (fast, clean rollback)
- Test database setup/teardown
- Session fixtures for tests

CRITICAL: Uses TEST_DATABASE_URL (separate from production DATABASE_URL).
NEVER connects to production database.
"""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base

# Test database URL (separate from production)
# Use environment variable if set, otherwise default to local test DB
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+pg8000://payroll:payroll@localhost:9174/payroll_test",
)

# CRITICAL: Synchronous engine with pg8000 driver (ICC standard)
engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database schema before tests, drop after tests."""
    Base.metadata.create_all(bind=engine)

    yield  # Run tests

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope for tests.

    Each test gets a clean database state via SAVEPOINT:
    1. Open connection and begin transaction
    2. Create Session bound to that connection with SAVEPOINT mode
    3. Run test — session.commit() creates SAVEPOINTs, not real commits
    4. ROLLBACK outer transaction (undo all test changes)
    5. Close connection

    This is fast and ensures complete test isolation.
    """
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
