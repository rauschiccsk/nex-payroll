"""Service layer for AuditLog entity.

Provides CRUD operations over the public.audit_log table.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate


def list_audit_logs(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditLog]:
    """Return a paginated list of audit log entries.

    Ordered by ``created_at`` descending (newest first).
    """
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
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
    """Partially update an existing audit log entry.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.

    Note: audit log entries are immutable by design; this function
    exists for API consistency.
    """
    entry = db.get(AuditLog, audit_log_id)
    if entry is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    db.flush()
    return entry


def delete_audit_log(db: Session, audit_log_id: UUID) -> bool:
    """Delete an audit log entry by primary key.

    Returns ``True`` if the row was deleted, ``False`` if not found.
    """
    entry = db.get(AuditLog, audit_log_id)
    if entry is None:
        return False

    db.delete(entry)
    db.flush()
    return True
