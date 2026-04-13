"""Service layer for AuditLog entity.

Provides CRUD operations over the public.audit_log table.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate

# ---------------------------------------------------------------------------
# write_audit helper — called by service layer for NR-05 compliance
# ---------------------------------------------------------------------------

_ACTION_MAP = {
    "create": "CREATE",
    "update": "UPDATE",
    "delete": "DELETE",
    # Accept uppercase directly too
    "CREATE": "CREATE",
    "UPDATE": "UPDATE",
    "DELETE": "DELETE",
}


def write_audit(
    db: Session,
    tenant_id: UUID,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    """Write an audit log entry and flush (no commit).

    action: 'create'|'update'|'delete' (case-insensitive) or uppercase variant.
    entity_id: UUID of the affected entity.
    Called by Employee, Contract, User, and Payroll service functions.
    """
    normalised_action = _ACTION_MAP.get(action)
    if normalised_action is None:
        raise ValueError(f"Invalid audit action={action!r}. Expected create/update/delete.")

    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=normalised_action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
    )
    db.add(entry)
    db.flush()


def _apply_filters(
    stmt,
    *,
    tenant_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    """Apply optional filters to a SELECT statement."""
    if tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if date_from is not None:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    return stmt


def count_audit_logs(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> int:
    """Return the total number of audit log entries matching filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(AuditLog)
    stmt = _apply_filters(
        stmt,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
    return db.execute(stmt).scalar_one()


def list_audit_logs(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    tenant_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AuditLog]:
    """Return a paginated list of audit log entries.

    Ordered by ``created_at`` descending (newest first).
    Supports optional filtering by tenant_id, entity_type, entity_id,
    user_id, and action.
    """
    stmt = select(AuditLog)
    stmt = _apply_filters(
        stmt,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_audit_log(db: Session, audit_log_id: UUID) -> AuditLog | None:
    """Return a single audit log entry by primary key, or ``None``."""
    return db.get(AuditLog, audit_log_id)


def create_audit_log(
    db: Session,
    payload: AuditLogCreate,
) -> AuditLog:
    """Insert a new audit log entry and flush (no commit)."""
    entry = AuditLog(**payload.model_dump())
    db.add(entry)
    db.flush()
    return entry


def update_audit_log(
    db: Session,
    audit_log_id: UUID,
    payload: AuditLogUpdate,
) -> AuditLog | None:
    """Update metadata fields of an audit log entry.

    Only non-identity fields (old_values, new_values, ip_address) may be
    changed.  Returns ``None`` when *audit_log_id* does not exist.
    """
    entry = db.get(AuditLog, audit_log_id)
    if entry is None:
        return None
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)
    db.flush()
    return entry


def delete_audit_log(db: Session, audit_log_id: UUID) -> bool:
    """Delete an audit log entry by primary key.

    Returns ``True`` when the entry was deleted, ``False`` when not found.
    """
    entry = db.get(AuditLog, audit_log_id)
    if entry is None:
        return False
    db.delete(entry)
    db.flush()
    return True
