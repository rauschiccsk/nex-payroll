"""Alembic environment configuration.

Reads DATABASE_URL from environment, imports all models for autogenerate.
Uses render_as_batch=True as required by DESIGN.md.
"""

import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# Alembic Config object
config = context.config

# Setup Python logging from ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from DATABASE_URL env var
database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Import all models so autogenerate can detect them
from app.models import Base  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402, F401
from app.models.contract import Contract  # noqa: E402, F401
from app.models.contribution_rate import ContributionRate  # noqa: E402, F401
from app.models.employee import Employee  # noqa: E402, F401
from app.models.employee_child import EmployeeChild  # noqa: E402, F401
from app.models.health_insurer import HealthInsurer  # noqa: E402, F401
from app.models.leave import Leave  # noqa: E402, F401
from app.models.leave_entitlement import LeaveEntitlement  # noqa: E402, F401
from app.models.monthly_report import MonthlyReport  # noqa: E402, F401
from app.models.notification import Notification  # noqa: E402, F401
from app.models.payment_order import PaymentOrder  # noqa: E402, F401
from app.models.statutory_deadline import StatutoryDeadline  # noqa: E402, F401
from app.models.tax_bracket import TaxBracket  # noqa: E402, F401
from app.models.tenant import Tenant  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (SQL script generation)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct DB connection)."""
    url = config.get_main_option("sqlalchemy.url")

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
