from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import settings
from app.routers.audit_log import router as audit_log_router
from app.routers.contracts import router as contracts_router
from app.routers.contribution_rates import router as contribution_rates_router
from app.routers.employee_children import router as employee_children_router
from app.routers.employees import router as employees_router
from app.routers.health_insurers import router as health_insurers_router
from app.routers.leave_entitlements import router as leave_entitlements_router
from app.routers.leaves import router as leaves_router
from app.routers.monthly_reports import router as monthly_reports_router
from app.routers.notifications import router as notifications_router
from app.routers.pay_slips import router as pay_slips_router
from app.routers.payment_orders import router as payment_orders_router
from app.routers.payroll import router as payroll_router
from app.routers.statutory_deadlines import router as statutory_deadlines_router
from app.routers.tax_brackets import router as tax_brackets_router
from app.routers.tenants import router as tenants_router
from app.routers.users import router as users_router

app = FastAPI(
    title=settings.app_name,
    description="Payroll management system for Slovak businesses",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    audit_log_router,
    prefix="/api/v1/audit-logs",
)
app.include_router(
    contracts_router,
    prefix="/api/v1/contracts",
)
app.include_router(
    contribution_rates_router,
    prefix="/api/v1/contribution-rates",
)
app.include_router(
    employee_children_router,
    prefix="/api/v1/employee-children",
)
app.include_router(
    employees_router,
    prefix="/api/v1/employees",
)
app.include_router(
    health_insurers_router,
    prefix="/api/v1/health-insurers",
)
app.include_router(
    leave_entitlements_router,
    prefix="/api/v1/leave-entitlements",
)
app.include_router(
    leaves_router,
    prefix="/api/v1/leaves",
)
app.include_router(
    monthly_reports_router,
    prefix="/api/v1/monthly-reports",
)
app.include_router(
    notifications_router,
    prefix="/api/v1/notifications",
)
app.include_router(
    payment_orders_router,
    prefix="/api/v1/payment-orders",
)
app.include_router(
    pay_slips_router,
    prefix="/api/v1/pay-slips",
)
app.include_router(
    payroll_router,
    prefix="/api/v1/payroll",
)
app.include_router(
    statutory_deadlines_router,
    prefix="/api/v1/statutory-deadlines",
)
app.include_router(
    tax_brackets_router,
    prefix="/api/v1/tax-brackets",
)
app.include_router(
    tenants_router,
    prefix="/api/v1/tenants",
)
app.include_router(
    users_router,
    prefix="/api/v1/users",
)


@app.get("/health")
def health_check():
    """Public. Service health check."""
    return {"status": "healthy", "version": __version__, "app": settings.app_name}
