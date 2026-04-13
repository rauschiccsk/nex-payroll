"""Service layer for Payroll entity.

Provides CRUD operations over the payrolls table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.pay_slip import PaySlip
from app.models.payroll import Payroll
from app.schemas.payroll import PayrollCreate, PayrollUpdate
from app.services.audit_log import write_audit

# ---------------------------------------------------------------------------
# Allowed enum values (validated at service level)
# ---------------------------------------------------------------------------

ALLOWED_STATUSES = frozenset({"draft", "calculated", "approved", "paid"})
ALLOWED_LEDGER_SYNC_STATUSES = frozenset({"pending", "synced", "error"})


def _validate_status(value: str | None) -> None:
    """Raise ``ValueError`` if *value* is not a recognised payroll status."""
    if value is not None and value not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status={value!r}. Allowed values: {sorted(ALLOWED_STATUSES)}")


def _validate_ledger_sync_status(value: str | None) -> None:
    """Raise ``ValueError`` if *value* is not a recognised ledger_sync_status."""
    if value is not None and value not in ALLOWED_LEDGER_SYNC_STATUSES:
        raise ValueError(
            f"Invalid ledger_sync_status={value!r}. Allowed values: {sorted(ALLOWED_LEDGER_SYNC_STATUSES)}"
        )


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


def count_payrolls(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    status: str | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
) -> int:
    """Return the total number of payrolls matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    _validate_status(status)

    stmt = select(func.count()).select_from(Payroll)

    if tenant_id is not None:
        stmt = stmt.where(Payroll.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(Payroll.employee_id == employee_id)

    if status is not None:
        stmt = stmt.where(Payroll.status == status)

    if period_year is not None:
        stmt = stmt.where(Payroll.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(Payroll.period_month == period_month)

    return db.execute(stmt).scalar_one()


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def list_payrolls(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    status: str | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Payroll]:
    """Return a paginated list of payrolls ordered by period (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *employee_id* is provided the result is filtered to that employee.
    When *status* is provided the result is filtered by status.
    When *period_year* / *period_month* are provided the result is filtered
    to the given period.
    """
    _validate_status(status)

    stmt = select(Payroll).order_by(
        Payroll.period_year.desc(),
        Payroll.period_month.desc(),
    )

    if tenant_id is not None:
        stmt = stmt.where(Payroll.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(Payroll.employee_id == employee_id)

    if status is not None:
        stmt = stmt.where(Payroll.status == status)

    if period_year is not None:
        stmt = stmt.where(Payroll.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(Payroll.period_month == period_month)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


def get_payroll(db: Session, payroll_id: UUID) -> Payroll | None:
    """Return a single payroll by primary key, or ``None``."""
    return db.get(Payroll, payroll_id)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def create_payroll(
    db: Session,
    payload: PayrollCreate,
    user_id: UUID | None = None,
) -> Payroll:
    """Insert a new payroll record and flush (no commit).

    Validates *status* at the service level before persisting.
    Raises ``ValueError`` if a payroll with the same
    ``(tenant_id, employee_id, period_year, period_month)`` already exists.
    """
    _validate_status(payload.status)

    dup_stmt = select(Payroll).where(
        Payroll.tenant_id == payload.tenant_id,
        Payroll.employee_id == payload.employee_id,
        Payroll.period_year == payload.period_year,
        Payroll.period_month == payload.period_month,
    )
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(
            f"Payroll for employee_id={payload.employee_id}, "
            f"period={payload.period_year}/{payload.period_month} "
            f"already exists in tenant {payload.tenant_id}"
        )

    payroll = Payroll(**payload.model_dump())
    db.add(payroll)
    db.flush()
    write_audit(
        db,
        tenant_id=payload.tenant_id,
        user_id=user_id,
        action="create",
        entity_type="Payroll",
        entity_id=payroll.id,
        new_values={k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                    for k, v in payload.model_dump().items()},
    )
    return payroll


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def update_payroll(
    db: Session,
    payroll_id: UUID,
    payload: PayrollUpdate,
    user_id: UUID | None = None,
) -> Payroll:
    """Partially update an existing payroll record.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the payroll is not found or if status/ledger
    values are invalid.
    """
    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data:
        _validate_status(update_data["status"])
    if "ledger_sync_status" in update_data:
        _validate_ledger_sync_status(update_data["ledger_sync_status"])

    payroll = db.get(Payroll, payroll_id)
    if payroll is None:
        raise ValueError(f"Payroll with id={payroll_id} not found")

    old_values = {k: str(getattr(payroll, k)) if not isinstance(getattr(payroll, k), (str, int, float, bool, type(None))) else getattr(payroll, k)
                  for k in update_data}

    for field, value in update_data.items():
        setattr(payroll, field, value)

    db.flush()
    write_audit(
        db,
        tenant_id=payroll.tenant_id,
        user_id=user_id,
        action="update",
        entity_type="Payroll",
        entity_id=payroll.id,
        old_values=old_values,
        new_values={k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                    for k, v in update_data.items()},
    )
    return payroll


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def delete_payroll(db: Session, payroll_id: UUID) -> bool:
    """Delete a payroll by primary key (hard delete).

    Returns ``True`` if the row was deleted.
    Raises ``ValueError`` if the payroll is not found.
    """
    payroll = db.get(Payroll, payroll_id)
    if payroll is None:
        raise ValueError(f"Payroll with id={payroll_id} not found")

    # Check FK dependencies — PaySlip references payroll
    pay_slip_count = db.execute(
        select(func.count()).select_from(PaySlip).where(PaySlip.payroll_id == payroll_id)
    ).scalar_one()
    if pay_slip_count > 0:
        raise ValueError(f"Cannot delete payroll id={payroll_id}: {pay_slip_count} pay slip(s) depend on it")

    db.delete(payroll)
    db.flush()
    return True
