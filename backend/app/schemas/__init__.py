"""Pydantic v2 request/response schemas for NEX Payroll API."""

from app.schemas.audit_log import AuditLogCreate, AuditLogRead
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    Token,
    TokenPayload,
)
from app.schemas.contract import ContractCreate, ContractRead, ContractUpdate
from app.schemas.contribution_rate import (
    ContributionRateCreate,
    ContributionRateRead,
    ContributionRateUpdate,
)
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.schemas.employee_child import (
    EmployeeChildCreate,
    EmployeeChildRead,
    EmployeeChildUpdate,
)
from app.schemas.health_insurer import (
    HealthInsurerCreate,
    HealthInsurerRead,
    HealthInsurerUpdate,
)
from app.schemas.leave import LeaveCreate, LeaveRead, LeaveUpdate
from app.schemas.leave_entitlement import (
    LeaveEntitlementCreate,
    LeaveEntitlementRead,
    LeaveEntitlementUpdate,
)
from app.schemas.monthly_report import (
    MonthlyReportCreate,
    MonthlyReportRead,
    MonthlyReportUpdate,
)
from app.schemas.notification import (
    NotificationCreate,
    NotificationRead,
    NotificationUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.schemas.pay_slip import PaySlipCreate, PaySlipRead, PaySlipUpdate
from app.schemas.payment_order import (
    PaymentOrderCreate,
    PaymentOrderRead,
    PaymentOrderUpdate,
)
from app.schemas.payroll import PayrollCreate, PayrollRead, PayrollUpdate
from app.schemas.statutory_deadline import (
    StatutoryDeadlineCreate,
    StatutoryDeadlineRead,
    StatutoryDeadlineUpdate,
)
from app.schemas.tax_bracket import (
    TaxBracketCreate,
    TaxBracketRead,
    TaxBracketUpdate,
)
from app.schemas.tenant import (
    TenantBase,
    TenantCreate,
    TenantInDB,
    TenantPublic,
    TenantRead,
    TenantUpdate,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserInDB,
    UserPublic,
    UserRead,
    UserUpdate,
)

__all__ = [
    "ChangePasswordRequest",
    "LoginRequest",
    "LoginResponse",
    "PaginatedResponse",
    "Token",
    "TokenPayload",
    "AuditLogCreate",
    "AuditLogRead",
    "ContractCreate",
    "ContractRead",
    "ContractUpdate",
    "ContributionRateCreate",
    "ContributionRateRead",
    "ContributionRateUpdate",
    "EmployeeCreate",
    "EmployeeRead",
    "EmployeeUpdate",
    "EmployeeChildCreate",
    "EmployeeChildRead",
    "EmployeeChildUpdate",
    "HealthInsurerCreate",
    "HealthInsurerRead",
    "HealthInsurerUpdate",
    "LeaveCreate",
    "LeaveRead",
    "LeaveUpdate",
    "LeaveEntitlementCreate",
    "LeaveEntitlementRead",
    "LeaveEntitlementUpdate",
    "MonthlyReportCreate",
    "MonthlyReportRead",
    "MonthlyReportUpdate",
    "NotificationCreate",
    "NotificationRead",
    "NotificationUpdate",
    "PaySlipCreate",
    "PaySlipRead",
    "PaySlipUpdate",
    "PaymentOrderCreate",
    "PaymentOrderRead",
    "PaymentOrderUpdate",
    "PayrollCreate",
    "PayrollRead",
    "PayrollUpdate",
    "StatutoryDeadlineCreate",
    "StatutoryDeadlineRead",
    "StatutoryDeadlineUpdate",
    "TaxBracketCreate",
    "TaxBracketRead",
    "TaxBracketUpdate",
    "TenantBase",
    "TenantCreate",
    "TenantInDB",
    "TenantPublic",
    "TenantRead",
    "TenantUpdate",
    "UserBase",
    "UserCreate",
    "UserInDB",
    "UserPublic",
    "UserRead",
    "UserUpdate",
]
