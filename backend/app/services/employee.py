"""Service layer for Employee entity.

Provides CRUD operations over the employees table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.

Soft-delete via ``is_deleted`` flag — list excludes deleted records
by default.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


def list_employees(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
) -> list[Employee]:
    """Return a paginated list of employees ordered by last_name, first_name.

    When *tenant_id* is provided the result is scoped to that tenant.
    Soft-deleted records are excluded unless *include_deleted* is ``True``.
    """
    stmt = select(Employee).order_by(Employee.last_name, Employee.first_name)

    if tenant_id is not None:
        stmt = stmt.where(Employee.tenant_id == tenant_id)

    if not include_deleted:
        stmt = stmt.where(Employee.is_deleted.is_(False))

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_employee(db: Session, employee_id: UUID) -> Employee | None:
    """Return a single employee by primary key, or ``None``."""
    return db.get(Employee, employee_id)


def create_employee(
    db: Session,
    payload: EmployeeCreate,
) -> Employee:
    """Insert a new employee and flush (no commit).

    Raises ``ValueError`` if an employee with the same
    ``(tenant_id, employee_number)`` already exists.
    """
    dup_stmt = select(Employee).where(
        Employee.tenant_id == payload.tenant_id,
        Employee.employee_number == payload.employee_number,
    )
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(
            f"Employee with employee_number={payload.employee_number!r} already exists in tenant {payload.tenant_id}"
        )

    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.flush()
    return employee


def update_employee(
    db: Session,
    employee_id: UUID,
    payload: EmployeeUpdate,
) -> Employee | None:
    """Partially update an existing employee.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    Raises ``ValueError`` if the update would create a duplicate
    ``(tenant_id, employee_number)``.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    # Check for duplicate employee_number if it is being changed
    new_number = update_data.get("employee_number")
    if new_number is not None and new_number != employee.employee_number:
        # Resolve the effective tenant_id (may also be changing)
        effective_tenant = update_data.get("tenant_id", employee.tenant_id)
        dup_stmt = select(Employee).where(
            Employee.tenant_id == effective_tenant,
            Employee.employee_number == new_number,
            Employee.id != employee_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(
                f"Employee with employee_number={new_number!r} already exists in tenant {effective_tenant}"
            )

    for field, value in update_data.items():
        setattr(employee, field, value)

    db.flush()
    return employee


def delete_employee(db: Session, employee_id: UUID) -> bool:
    """Delete an employee by primary key (hard delete).

    Returns ``True`` if the row was deleted, ``False`` if not found.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        return False

    db.delete(employee)
    db.flush()
    return True
