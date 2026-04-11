"""Service layer for Notification entity.

Provides CRUD operations over the notifications table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate


def count_notifications(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    is_read: bool | None = None,
    type: str | None = None,
    severity: str | None = None,
) -> int:
    """Return the total number of notifications matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(Notification)

    if tenant_id is not None:
        stmt = stmt.where(Notification.tenant_id == tenant_id)

    if user_id is not None:
        stmt = stmt.where(Notification.user_id == user_id)

    if is_read is not None:
        stmt = stmt.where(Notification.is_read == is_read)

    if type is not None:
        stmt = stmt.where(Notification.type == type)

    if severity is not None:
        stmt = stmt.where(Notification.severity == severity)

    return db.execute(stmt).scalar_one()


def list_notifications(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    is_read: bool | None = None,
    type: str | None = None,
    severity: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Notification]:
    """Return a paginated list of notifications ordered by created_at (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *user_id* is provided the result is further scoped to that user.
    When *is_read* is provided the result is filtered by read status.
    When *type* is provided the result is filtered by notification type.
    When *severity* is provided the result is filtered by severity level.
    """
    stmt = select(Notification).order_by(Notification.created_at.desc())

    if tenant_id is not None:
        stmt = stmt.where(Notification.tenant_id == tenant_id)

    if user_id is not None:
        stmt = stmt.where(Notification.user_id == user_id)

    if is_read is not None:
        stmt = stmt.where(Notification.is_read == is_read)

    if type is not None:
        stmt = stmt.where(Notification.type == type)

    if severity is not None:
        stmt = stmt.where(Notification.severity == severity)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_notification(db: Session, notification_id: UUID) -> Notification | None:
    """Return a single notification by primary key, or ``None``."""
    return db.get(Notification, notification_id)


def create_notification(
    db: Session,
    payload: NotificationCreate,
) -> Notification:
    """Insert a new notification record and flush (no commit)."""
    notification = Notification(**payload.model_dump())
    db.add(notification)
    db.flush()
    return notification


def update_notification(
    db: Session,
    notification_id: UUID,
    payload: NotificationUpdate,
) -> Notification:
    """Partially update an existing notification record.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the notification is not found.
    """
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise ValueError(f"Notification with id={notification_id} not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Never accept client-supplied read_at — always server-controlled.
    # Strip any client-supplied value before applying is_read logic.
    update_data.pop("read_at", None)

    # Set read_at server-side when is_read transitions to True; clear on False.
    if "is_read" in update_data:
        if update_data["is_read"] and not notification.is_read:
            update_data["read_at"] = datetime.now(UTC)
        elif not update_data["is_read"]:
            update_data["read_at"] = None

    for field, value in update_data.items():
        setattr(notification, field, value)

    db.flush()
    return notification


def delete_notification(db: Session, notification_id: UUID) -> bool:
    """Delete a notification by primary key (hard delete).

    Returns ``True`` if the row was deleted.
    Raises ``ValueError`` if the notification is not found.
    """
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise ValueError(f"Notification with id={notification_id} not found")

    db.delete(notification)
    db.flush()
    return True
