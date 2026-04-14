"""Synchronous SQLAlchemy engine and session factory.

Uses pg8000 driver — NEVER asyncpg.

Tenant isolation: TenantResolverMiddleware sets ``tenant_schema_var``
context variable; ``get_db`` reads it and issues
``SET search_path TO {schema}, public`` on the session connection.
"""

import contextvars
import re

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Context variable set by TenantResolverMiddleware, read by get_db.
tenant_schema_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_schema",
    default=None,
)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_db():
    """FastAPI dependency — yields a DB session per request.

    If ``tenant_schema_var`` has been set by TenantResolverMiddleware,
    the session's connection search_path is switched to the tenant
    schema before yielding.  This is reset on connection return to pool.
    """
    db = SessionLocal()
    try:
        schema = tenant_schema_var.get()
        if schema is not None:
            # Validate schema name against strict pattern to prevent SQL injection
            if not re.match(r"^[a-z_][a-z0-9_]*$", schema):
                raise ValueError(f"Invalid schema name: {schema!r}")
            db.execute(text(f"SET search_path TO {schema}, shared, public"))
        yield db
    finally:
        if tenant_schema_var.get() is not None:
            # Reset search_path so pooled connection is clean
            db.execute(text("SET search_path TO public"))
        db.close()
