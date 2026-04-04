"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.base import Base
from app.models.contribution_rate import ContributionRate

__all__ = ["Base", "ContributionRate"]
