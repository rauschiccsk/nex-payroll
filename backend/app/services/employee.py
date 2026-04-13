"""Service layer for Employee entity.

Provides CRUD operations over the employees table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.

Soft-delete via ``is_deleted`` flag — list excludes deleted records
by default.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.audit_log import write_audit


def count_employees(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    status: str | None = None,
    include_deleted: bool = False,
) -> int:
    """Return the total number of employees (respecting filters).

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(Employee)

    if tenant_id is not None:
        stmt = stmt.where(Employee.tenant_id == tenant_id)

    if status is not None:
        stmt = stmt.where(Employee.status == status)

    if not include_deleted:
        stmt = stmt.where(Employee.is_deleted.is_(False))

    return db.execute(stmt).scalar_one()


def list_employees(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
) -> list[Employee]:
    """Return a paginated list of employees ordered by last_name, first_name.

    When *tenant_id* is provided the result is scoped to that tenant.
    When *status* is provided the result is filtered by employee status.
    Soft-deleted records are excluded unless *include_deleted* is ``True``.
    """
    stmt = select(Employee).order_by(Employee.last_name, Employee.first_name)

    if tenant_id is not None:
        stmt = stmt.where(Employee.tenant_id == tenant_id)

    if status is not None:
        stmt = stmt.where(Employee.status == status)

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
    user_id: UUID | None = None,
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
    write_audit(
        db,
        tenant_id=payload.tenant_id,
        user_id=user_id,
        action="create",
        entity_type="Employee",
        entity_id=employee.id,
        new_values={
            k: str(v) if not isinstance(v, str | int | float | bool | type(None)) else v
            for k, v in payload.model_dump().items()
        },
    )
    return employee


def update_employee(
    db: Session,
    employee_id: UUID,
    payload: EmployeeUpdate,
    user_id: UUID | None = None,
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
        dup_stmt = select(Employee).where(
            Employee.tenant_id == employee.tenant_id,
            Employee.employee_number == new_number,
            Employee.id != employee_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(
                f"Employee with employee_number={new_number!r} already exists in tenant {employee.tenant_id}"
            )

    old_values = {
        k: str(getattr(employee, k))
        if not isinstance(getattr(employee, k), str | int | float | bool | type(None))
        else getattr(employee, k)
        for k in update_data
    }

    for field, value in update_data.items():
        setattr(employee, field, value)

    db.flush()
    write_audit(
        db,
        tenant_id=employee.tenant_id,
        user_id=user_id,
        action="update",
        entity_type="Employee",
        entity_id=employee.id,
        old_values=old_values,
        new_values={
            k: str(v) if not isinstance(v, str | int | float | bool | type(None)) else v for k, v in update_data.items()
        },
    )
    return employee


def delete_employee(db: Session, employee_id: UUID, user_id: UUID | None = None) -> bool:
    """Soft-delete an employee by setting ``is_deleted = True``.

    Returns ``True`` if the employee was found and soft-deleted,
    ``False`` if not found.
    """
    employee = db.get(Employee, employee_id)
    if employee is None:
        return False

    employee.is_deleted = True
    db.flush()
    write_audit(
        db,
        tenant_id=employee.tenant_id,
        user_id=user_id,
        action="delete",
        entity_type="Employee",
        entity_id=employee.id,
        old_values={"is_deleted": False},
        new_values={"is_deleted": True},
    )
    return True
