"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.base import Base
from app.models.contribution_rate import ContributionRate
from app.models.health_insurer import HealthInsurer
from app.models.statutory_deadline import StatutoryDeadline
from app.models.tax_bracket import TaxBracket
from app.models.tenant import Tenant

__all__ = [
    "Base",
    "ContributionRate",
    "HealthInsurer",
    "StatutoryDeadline",
    "TaxBracket",
    "Tenant",
]
