"""SQLAlchemy declarative base and shared mixins.

All models MUST use:
- UUIDMixin for primary key
- TimestampMixin for created_at / updated_at
- server_default for all defaults (NEVER Python-side)
- TIMESTAMP(timezone=True) for all datetime columns
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Declarative base for all NEX Payroll models."""


class UUIDMixin:
    """Provides a UUID primary key with server-side default."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """Provides created_at and updated_at with server-side defaults.

    NEVER use datetime.utcnow (deprecated in Python 3.12).
    Always func.now() for server_default and onupdate.
    """

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
