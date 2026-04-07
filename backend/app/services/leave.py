"""Service layer for Leave entity.

Provides CRUD operations over the leaves table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.leave import Leave
from app.models.tenant import Tenant
from app.schemas.leave import LeaveCreate, LeaveUpdate


def count_leaves(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    status: str | None = None,
) -> int:
    """Return the total number of leaves matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(Leave)

    if tenant_id is not None:
        stmt = stmt.where(Leave.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(Leave.employee_id == employee_id)

    if status is not None:
        stmt = stmt.where(Leave.status == status)

    return db.execute(stmt).scalar_one()


def list_leaves(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Leave]:
    """Return a paginated list of leaves ordered by start_date (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *employee_id* is provided the result is further scoped to that employee.
    When *status* is provided the result is filtered to that status.
    """
    stmt = select(Leave).order_by(Leave.start_date.desc())

    if tenant_id is not None:
        stmt = stmt.where(Leave.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(Leave.employee_id == employee_id)

    if status is not None:
        stmt = stmt.where(Leave.status == status)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_leave(db: Session, leave_id: UUID) -> Leave | None:
    """Return a single leave by primary key, or ``None``."""
    return db.get(Leave, leave_id)


def create_leave(
    db: Session,
    payload: LeaveCreate,
) -> Leave:
    """Insert a new leave record and flush (no commit).

    Validates that referenced tenant and employee exist before inserting.
    Raises ``ValueError`` if either foreign key reference is invalid.
    """
    tenant = db.get(Tenant, payload.tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={payload.tenant_id} not found")

    employee = db.get(Employee, payload.employee_id)
    if employee is None:
        raise ValueError(f"Employee with id={payload.employee_id} not found")

    leave = Leave(**payload.model_dump())
    db.add(leave)
    db.flush()
    return leave


def update_leave(
    db: Session,
    leave_id: UUID,
    payload: LeaveUpdate,
) -> Leave:
    """Partially update an existing leave record.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the leave is not found.
    """
    leave = db.get(Leave, leave_id)
    if leave is None:
        raise ValueError(f"Leave with id={leave_id} not found")

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(leave, field, value)

    db.flush()
    return leave


def delete_leave(db: Session, leave_id: UUID) -> bool:
    """Delete a leave by primary key (hard delete).

    Returns ``True`` if the row was deleted.
    Raises ``ValueError`` if the leave is not found.
    """
    leave = db.get(Leave, leave_id)
    if leave is None:
        raise ValueError(f"Leave with id={leave_id} not found")

    db.delete(leave)
    db.flush()
    return True
