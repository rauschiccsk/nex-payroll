"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.contract import Contract
from app.models.contribution_rate import ContributionRate
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.statutory_deadline import StatutoryDeadline
from app.models.tax_bracket import TaxBracket
from app.models.tenant import Tenant

__all__ = [
    "AuditLog",
    "Base",
    "Contract",
    "ContributionRate",
    "Employee",
    "HealthInsurer",
    "StatutoryDeadline",
    "TaxBracket",
    "Tenant",
]
