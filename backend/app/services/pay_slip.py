"""Service layer for PaySlip entity.

Provides CRUD operations over the pay_slips table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pay_slip import PaySlip
from app.schemas.pay_slip import PaySlipCreate, PaySlipUpdate


def count_pay_slips(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    payroll_id: UUID | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
) -> int:
    """Return the total number of pay slips matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(PaySlip)

    if tenant_id is not None:
        stmt = stmt.where(PaySlip.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(PaySlip.employee_id == employee_id)

    if payroll_id is not None:
        stmt = stmt.where(PaySlip.payroll_id == payroll_id)

    if period_year is not None:
        stmt = stmt.where(PaySlip.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(PaySlip.period_month == period_month)

    return db.execute(stmt).scalar_one()


def list_pay_slips(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    payroll_id: UUID | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[PaySlip]:
    """Return a paginated list of pay slips ordered by period (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *employee_id* is provided the result is filtered to that employee.
    When *payroll_id* is provided the result is filtered to that payroll.
    When *period_year* / *period_month* are provided the result is filtered
    to the given period.
    """
    stmt = select(PaySlip).order_by(
        PaySlip.period_year.desc(),
        PaySlip.period_month.desc(),
    )

    if tenant_id is not None:
        stmt = stmt.where(PaySlip.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(PaySlip.employee_id == employee_id)

    if payroll_id is not None:
        stmt = stmt.where(PaySlip.payroll_id == payroll_id)

    if period_year is not None:
        stmt = stmt.where(PaySlip.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(PaySlip.period_month == period_month)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_pay_slip(db: Session, pay_slip_id: UUID) -> PaySlip | None:
    """Return a single pay slip by primary key, or ``None``."""
    return db.get(PaySlip, pay_slip_id)


def create_pay_slip(
    db: Session,
    payload: PaySlipCreate,
) -> PaySlip:
    """Insert a new pay slip record and flush (no commit).

    Raises ``ValueError`` if a pay slip with the same
    ``(tenant_id, payroll_id)`` already exists.
    """
    dup_stmt = select(PaySlip).where(
        PaySlip.tenant_id == payload.tenant_id,
        PaySlip.payroll_id == payload.payroll_id,
    )
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"PaySlip for payroll_id={payload.payroll_id} already exists in tenant {payload.tenant_id}")

    pay_slip = PaySlip(**payload.model_dump())
    db.add(pay_slip)
    db.flush()
    return pay_slip


def update_pay_slip(
    db: Session,
    pay_slip_id: UUID,
    payload: PaySlipUpdate,
) -> PaySlip:
    """Partially update an existing pay slip record.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the pay slip is not found or if the update
    would create a duplicate ``(tenant_id, payroll_id)``.
    """
    pay_slip = db.get(PaySlip, pay_slip_id)
    if pay_slip is None:
        raise ValueError(f"PaySlip with id={pay_slip_id} not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Check for duplicate (tenant_id, payroll_id) if payroll_id is being changed
    new_payroll_id = update_data.get("payroll_id")
    if new_payroll_id is not None and new_payroll_id != pay_slip.payroll_id:
        dup_stmt = select(PaySlip).where(
            PaySlip.tenant_id == pay_slip.tenant_id,
            PaySlip.payroll_id == new_payroll_id,
            PaySlip.id != pay_slip_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(f"PaySlip for payroll_id={new_payroll_id} already exists in tenant {pay_slip.tenant_id}")

    for field, value in update_data.items():
        setattr(pay_slip, field, value)

    db.flush()
    return pay_slip


def delete_pay_slip(db: Session, pay_slip_id: UUID) -> bool:
    """Delete a pay slip by primary key (hard delete).

    Returns ``True`` if the row was deleted.
    Raises ``ValueError`` if the pay slip is not found.
    """
    pay_slip = db.get(PaySlip, pay_slip_id)
    if pay_slip is None:
        raise ValueError(f"PaySlip with id={pay_slip_id} not found")

    db.delete(pay_slip)
    db.flush()
    return True
