"""Service layer for AuditLog entity.

Provides read and create operations over the public.audit_log table.
Audit log entries are immutable — no update or delete operations exist.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate


def _apply_filters(
    stmt,
    *,
    tenant_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
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
    return stmt


def count_audit_logs(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    action: str | None = None,
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
    """Insert a new audit log entry and flush (no commit).

    This function is intended for internal use only — audit entries
    are created by the system when CRUD operations occur on other entities.
    """
    entry = AuditLog(**payload.model_dump())
    db.add(entry)
    db.flush()
    return entry
