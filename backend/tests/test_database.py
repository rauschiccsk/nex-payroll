"""Tests for database engine and session factory (app.core.database)."""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal, engine, get_db


def test_engine_is_created():
    """Verify SQLAlchemy engine is instantiated."""
    assert engine is not None
    assert isinstance(engine, Engine)


def test_engine_uses_pg8000_driver():
    """Verify engine URL uses pg8000 driver (NEVER asyncpg)."""
    url_str = str(engine.url)
    assert "pg8000" in url_str
    assert "asyncpg" not in url_str


def test_engine_pool_pre_ping_enabled():
    """Verify pool_pre_ping is True for connection health checks."""
    assert engine.pool._pre_ping is True


def test_session_local_is_sessionmaker():
    """Verify SessionLocal is a proper sessionmaker."""
    assert isinstance(SessionLocal, sessionmaker)


def test_session_local_expire_on_commit_false():
    """Verify expire_on_commit=False for post-commit attribute access."""
    assert SessionLocal.kw.get("expire_on_commit") is False


def test_get_db_yields_session():
    """Verify get_db generator yields a Session and closes it."""
    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    # Cleanup: close the generator (triggers finally block)
    gen.close()
