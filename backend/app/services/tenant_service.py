"""Service layer for Tenant entity.

Provides CRUD operations over the public.tenants table.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

import re
import unicodedata
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.employee import Employee
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantUpdate


def _generate_schema_name(name: str, ico: str) -> str:
    """Derive a PostgreSQL schema name from the company name and IČO.

    Rules:
    - Lowercase, ASCII-only (diacritics stripped).
    - Spaces / special chars replaced with underscores.
    - Prefixed with ``tenant_`` and suffixed with ``_<ico>``.
    - Maximum 63 characters (PG identifier limit).
    """
    # NFD decomposition → strip combining marks → lowercase
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = ascii_name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    # Limit the slug so total stays within 63 chars:
    # "tenant_" (7) + slug + "_" (1) + ico (8) = 16 + slug
    max_slug = 63 - 7 - 1 - len(ico)
    slug = slug[:max_slug]
    return f"tenant_{slug}_{ico}"


def count_tenants(db: Session, *, is_active: bool | None = None) -> int:
    """Return the total number of tenants, optionally filtered by active status.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(Tenant)
    if is_active is not None:
        stmt = stmt.where(Tenant.is_active == is_active)
    return db.execute(stmt).scalar_one()


def list_tenants(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
) -> list[Tenant]:
    """Return a paginated list of tenants ordered by name, optionally filtered."""
    stmt = select(Tenant).order_by(Tenant.name).offset(skip).limit(limit)
    if is_active is not None:
        stmt = stmt.where(Tenant.is_active == is_active)
    return list(db.execute(stmt).scalars().all())


def get_tenant(db: Session, tenant_id: UUID) -> Tenant | None:
    """Return a single tenant by primary key, or ``None``."""
    return db.get(Tenant, tenant_id)


def create_tenant(
    db: Session,
    payload: TenantCreate,
) -> Tenant:
    """Insert a new tenant and flush (no commit).

    The ``schema_name`` is auto-generated from the company name and IČO.
    Raises ``ValueError`` if a tenant with the same IČO already exists.
    """
    # Check for duplicate IČO
    dup_stmt = select(Tenant).where(Tenant.ico == payload.ico)
    existing = db.execute(dup_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Tenant with ico={payload.ico!r} already exists")

    data = payload.model_dump()
    data["schema_name"] = _generate_schema_name(payload.name, payload.ico)

    # Ensure generated schema_name is also unique
    schema_dup = select(Tenant).where(Tenant.schema_name == data["schema_name"])
    if db.execute(schema_dup).scalar_one_or_none() is not None:
        raise ValueError(f"Tenant with schema_name={data['schema_name']!r} already exists")

    tenant = Tenant(**data)
    db.add(tenant)
    db.flush()
    return tenant


def update_tenant(
    db: Session,
    tenant_id: UUID,
    payload: TenantUpdate,
) -> Tenant | None:
    """Partially update an existing tenant.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    Raises ``ValueError`` if the update would create a duplicate IČO.
    """
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    # Check for duplicate IČO if ico is being updated
    if "ico" in update_data and update_data["ico"] != tenant.ico:
        dup_stmt = select(Tenant).where(
            Tenant.ico == update_data["ico"],
            Tenant.id != tenant_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none() is not None:
            raise ValueError(f"Tenant with ico={update_data['ico']!r} already exists")

    for field, value in update_data.items():
        setattr(tenant, field, value)

    db.flush()
    return tenant


def delete_tenant(db: Session, tenant_id: UUID) -> bool:
    """Delete a tenant by primary key.

    Returns ``True`` if the row was deleted.

    Raises:
        ValueError: If dependent records (users, employees, audit logs) exist.
    """
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        return False

    # Check FK dependencies before deletion
    user_count = db.scalar(select(func.count()).select_from(User).where(User.tenant_id == tenant_id))
    if user_count:
        raise ValueError(f"Cannot delete tenant: {user_count} dependent user(s) exist")

    employee_count = db.scalar(select(func.count()).select_from(Employee).where(Employee.tenant_id == tenant_id))
    if employee_count:
        raise ValueError(f"Cannot delete tenant: {employee_count} dependent employee(s) exist")

    audit_count = db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == tenant_id))
    if audit_count:
        raise ValueError(f"Cannot delete tenant: {audit_count} dependent audit log(s) exist")

    db.delete(tenant)
    db.flush()
    return True
