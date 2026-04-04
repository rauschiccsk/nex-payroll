"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.base import Base

__all__ = ["Base"]
