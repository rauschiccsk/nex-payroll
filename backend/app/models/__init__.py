"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.base import Base
from app.models.contribution_rate import ContributionRate
from app.models.health_insurer import HealthInsurer

__all__ = ["Base", "ContributionRate", "HealthInsurer"]
