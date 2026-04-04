"""Tests for SQLAlchemy base and mixins (app.models.base)."""

from sqlalchemy import TIMESTAMP, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase

from app.models.base import Base, TimestampMixin, UUIDMixin


def test_base_is_declarative_base():
    """Verify Base inherits from DeclarativeBase."""
    assert issubclass(Base, DeclarativeBase)


def test_uuid_mixin_id_column():
    """Verify UUIDMixin provides a UUID primary key with server_default."""

    class _TestModel(Base, UUIDMixin):
        __tablename__ = "_test_uuid_mixin"

    mapper = inspect(_TestModel)
    id_col = mapper.columns["id"]

    assert id_col.primary_key is True
    assert isinstance(id_col.type, UUID)
    assert id_col.server_default is not None


def test_timestamp_mixin_columns():
    """Verify TimestampMixin provides created_at and updated_at with TIMESTAMP(timezone=True)."""

    class _TestModel2(Base, UUIDMixin, TimestampMixin):
        __tablename__ = "_test_timestamp_mixin"

    mapper = inspect(_TestModel2)

    created_col = mapper.columns["created_at"]
    assert isinstance(created_col.type, TIMESTAMP)
    assert created_col.type.timezone is True
    assert created_col.nullable is False
    assert created_col.server_default is not None

    updated_col = mapper.columns["updated_at"]
    assert isinstance(updated_col.type, TIMESTAMP)
    assert updated_col.type.timezone is True
    assert updated_col.nullable is False
    assert updated_col.server_default is not None
    assert updated_col.onupdate is not None
