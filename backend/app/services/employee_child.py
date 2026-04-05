"""Service layer for EmployeeChild entity.

Provides CRUD operations over the employee_children table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee_child import EmployeeChild
from app.schemas.employee_child import EmployeeChildCreate, EmployeeChildUpdate


def count_employee_children(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
) -> int:
    """Return the total number of employee children matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(EmployeeChild)

    if tenant_id is not None:
        stmt = stmt.where(EmployeeChild.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(EmployeeChild.employee_id == employee_id)

    return db.execute(stmt).scalar_one()


def list_employee_children(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    employee_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[EmployeeChild]:
    """Return a paginated list of employee children ordered by last_name, first_name.

    When *tenant_id* is provided the result is scoped to that tenant.
    When *employee_id* is provided the result is further scoped to that employee.
    """
    stmt = select(EmployeeChild).order_by(EmployeeChild.last_name, EmployeeChild.first_name)

    if tenant_id is not None:
        stmt = stmt.where(EmployeeChild.tenant_id == tenant_id)

    if employee_id is not None:
        stmt = stmt.where(EmployeeChild.employee_id == employee_id)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_employee_child(db: Session, child_id: UUID) -> EmployeeChild | None:
    """Return a single employee child by primary key, or ``None``."""
    return db.get(EmployeeChild, child_id)


def create_employee_child(
    db: Session,
    payload: EmployeeChildCreate,
) -> EmployeeChild:
    """Insert a new employee child record and flush (no commit)."""
    child = EmployeeChild(**payload.model_dump())
    db.add(child)
    db.flush()
    return child


def update_employee_child(
    db: Session,
    child_id: UUID,
    payload: EmployeeChildUpdate,
) -> EmployeeChild | None:
    """Partially update an existing employee child record.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    """
    child = db.get(EmployeeChild, child_id)
    if child is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(child, field, value)

    db.flush()
    return child


def delete_employee_child(db: Session, child_id: UUID) -> bool:
    """Delete an employee child by primary key (hard delete).

    Returns ``True`` if the row was deleted, ``False`` if not found.
    """
    child = db.get(EmployeeChild, child_id)
    if child is None:
        return False

    db.delete(child)
    db.flush()
    return True
