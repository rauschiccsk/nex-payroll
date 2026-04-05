"""Service layer for LeaveEntitlement entity.

Provides CRUD operations over the leave_entitlements table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.leave_entitlement import LeaveEntitlement
from app.schemas.leave_entitlement import LeaveEntitlementCreate, LeaveEntitlementUpdate


def count_leave_entitlements(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    year: int | None = None,
) -> int:
    """Return the total number of leave entitlements matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(LeaveEntitlement)

    if tenant_id is not None:
        stmt = stmt.where(LeaveEntitlement.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(LeaveEntitlement.employee_id == employee_id)

    if year is not None:
        stmt = stmt.where(LeaveEntitlement.year == year)

    return db.execute(stmt).scalar_one()


def list_leave_entitlements(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    year: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[LeaveEntitlement]:
    """Return a paginated list of leave entitlements ordered by year (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *employee_id* is provided the result is further scoped to that employee.
    When *year* is provided the result is filtered to that calendar year.
    """
    stmt = select(LeaveEntitlement).order_by(LeaveEntitlement.year.desc())

    if tenant_id is not None:
        stmt = stmt.where(LeaveEntitlement.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(LeaveEntitlement.employee_id == employee_id)

    if year is not None:
        stmt = stmt.where(LeaveEntitlement.year == year)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_leave_entitlement(db: Session, entitlement_id: UUID) -> LeaveEntitlement | None:
    """Return a single leave entitlement by primary key, or ``None``."""
    return db.get(LeaveEntitlement, entitlement_id)


def create_leave_entitlement(
    db: Session,
    payload: LeaveEntitlementCreate,
) -> LeaveEntitlement:
    """Insert a new leave entitlement record and flush (no commit).

    Raises ``ValueError`` if an entitlement with the same
    ``(tenant_id, employee_id, year)`` already exists.
    """
    dup_stmt = select(LeaveEntitlement).where(
        LeaveEntitlement.tenant_id == payload.tenant_id,
        LeaveEntitlement.employee_id == payload.employee_id,
        LeaveEntitlement.year == payload.year,
    )
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(
            f"LeaveEntitlement for employee_id={payload.employee_id} "
            f"year={payload.year} already exists in tenant {payload.tenant_id}"
        )

    entitlement = LeaveEntitlement(**payload.model_dump())
    db.add(entitlement)
    db.flush()
    return entitlement


def update_leave_entitlement(
    db: Session,
    entitlement_id: UUID,
    payload: LeaveEntitlementUpdate,
) -> LeaveEntitlement:
    """Partially update an existing leave entitlement record.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the entitlement is not found.
    """
    entitlement = db.get(LeaveEntitlement, entitlement_id)
    if entitlement is None:
        raise ValueError(f"LeaveEntitlement with id={entitlement_id} not found")

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(entitlement, field, value)

    db.flush()
    return entitlement


def delete_leave_entitlement(db: Session, entitlement_id: UUID) -> bool:
    """Delete a leave entitlement by primary key (hard delete).

    Returns ``True`` if the row was deleted.
    Raises ``ValueError`` if the entitlement is not found.

    Currently no FK dependencies reference leave_entitlements directly.
    """
    entitlement = db.get(LeaveEntitlement, entitlement_id)
    if entitlement is None:
        raise ValueError(f"LeaveEntitlement with id={entitlement_id} not found")

    db.delete(entitlement)
    db.flush()
    return True
