"""Alembic environment configuration.

Reads DATABASE_URL from environment, imports all models for autogenerate.
Uses render_as_batch=True as required by DESIGN.md.
Supports multi-schema (public, shared, tenant) via include_schemas=True.
"""

import contextlib
import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

import app.models as _models  # noqa: F401
from alembic import context
from app.models.annual_settlement import AnnualSettlement  # noqa: F401
from app.models.base import Base
from app.models.journal_entry import JournalEntry  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.statutory_deadline import StatutoryDeadline  # noqa: F401

target_metadata = Base.metadata


def _get_url(config) -> str:
    """Return database URL from env var or alembic config."""
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    config = context.config
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    url = _get_url(config)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct DB connection)."""
    config = context.config
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    url = _get_url(config)

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations() -> None:
    """Dispatch to offline or online migration runner."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


# Alembic EnvironmentContext proxy is not established when env.py is
# imported as a regular module outside of the Alembic CLI runtime.
with contextlib.suppress(NameError):
    run_migrations()
