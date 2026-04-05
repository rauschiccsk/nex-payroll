"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can detect them.
"""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.contract import Contract
from app.models.contribution_rate import ContributionRate
from app.models.employee import Employee
from app.models.employee_child import EmployeeChild
from app.models.health_insurer import HealthInsurer
from app.models.leave import Leave
from app.models.leave_entitlement import LeaveEntitlement
from app.models.monthly_report import MonthlyReport
from app.models.notification import Notification
from app.models.pay_slip import PaySlip
from app.models.payment_order import PaymentOrder
from app.models.payroll import Payroll
from app.models.statutory_deadline import StatutoryDeadline
from app.models.tax_bracket import TaxBracket
from app.models.tenant import Tenant
from app.models.user import User

__all__ = [
    "AuditLog",
    "Base",
    "Contract",
    "ContributionRate",
    "Employee",
    "EmployeeChild",
    "HealthInsurer",
    "Leave",
    "LeaveEntitlement",
    "MonthlyReport",
    "Notification",
    "PaySlip",
    "PaymentOrder",
    "Payroll",
    "StatutoryDeadline",
    "TaxBracket",
    "Tenant",
    "User",
]
