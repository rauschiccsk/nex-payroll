"""Service layer — business logic and CRUD operations.

Import service modules directly (e.g. ``from app.services import leave_service``)
rather than importing individual functions.  This keeps router imports consistent
with the Router Generation Checklist pattern.
"""

from app.services import audit_log as audit_log_service
from app.services import contract as contract_service
from app.services import contribution_rate as contribution_rate_service
from app.services import employee as employee_service
from app.services import employee_child as employee_child_service
from app.services import health_insurer as health_insurer_service
from app.services import leave as leave_service
from app.services import leave_entitlement as leave_entitlement_service
from app.services import monthly_report as monthly_report_service
from app.services import notification as notification_service
from app.services import pay_slip as pay_slip_service
from app.services import payment_order as payment_order_service
from app.services import payroll as payroll_service
from app.services import statutory_deadline as statutory_deadline_service
from app.services import tax_bracket as tax_bracket_service
from app.services import tenant_service
from app.services import user as user_service

__all__ = [
    "audit_log_service",
    "contract_service",
    "contribution_rate_service",
    "employee_child_service",
    "employee_service",
    "health_insurer_service",
    "leave_entitlement_service",
    "leave_service",
    "monthly_report_service",
    "notification_service",
    "pay_slip_service",
    "payment_order_service",
    "payroll_service",
    "statutory_deadline_service",
    "tax_bracket_service",
    "tenant_service",
    "user_service",
]
