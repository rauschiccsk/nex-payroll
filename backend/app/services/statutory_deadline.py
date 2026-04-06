"""Service layer for StatutoryDeadline entity.

Provides CRUD operations over the shared.statutory_deadlines table.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session. They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.statutory_deadline import StatutoryDeadline
from app.schemas.statutory_deadline import StatutoryDeadlineCreate, StatutoryDeadlineUpdate


def count_statutory_deadlines(db: Session) -> int:
    """Return the total number of statutory deadlines.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(StatutoryDeadline)
    return db.execute(stmt).scalar_one()


def list_statutory_deadlines(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[StatutoryDeadline]:
    """Return a paginated list of statutory deadlines.

    Ordered by ``deadline_type`` then ``valid_from`` descending so the
    most-recent version of each deadline comes first.
    """
    stmt = (
        select(StatutoryDeadline)
        .order_by(StatutoryDeadline.deadline_type, StatutoryDeadline.valid_from.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_statutory_deadline(db: Session, deadline_id: UUID) -> StatutoryDeadline | None:
    """Return a single statutory deadline by primary key, or ``None``."""
    return db.get(StatutoryDeadline, deadline_id)


def create_statutory_deadline(
    db: Session,
    payload: StatutoryDeadlineCreate,
) -> StatutoryDeadline:
    """Insert a new statutory deadline and flush (no commit)."""
    deadline = StatutoryDeadline(**payload.model_dump())
    db.add(deadline)
    db.flush()
    return deadline


def update_statutory_deadline(
    db: Session,
    deadline_id: UUID,
    payload: StatutoryDeadlineUpdate,
) -> StatutoryDeadline | None:
    """Partially update an existing statutory deadline.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    """
    deadline = db.get(StatutoryDeadline, deadline_id)
    if deadline is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deadline, field, value)

    db.flush()
    return deadline


def delete_statutory_deadline(db: Session, deadline_id: UUID) -> bool:
    """Delete a statutory deadline by primary key.

    Returns ``True`` if the row was deleted, ``False`` if not found.
    """
    deadline = db.get(StatutoryDeadline, deadline_id)
    if deadline is None:
        return False

    db.delete(deadline)
    db.flush()
    return True
