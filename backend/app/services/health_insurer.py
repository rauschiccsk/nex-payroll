"""Service layer for HealthInsurer entity.

Provides CRUD operations over the shared.health_insurers table.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session. They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.health_insurer import HealthInsurer
from app.schemas.health_insurer import HealthInsurerCreate, HealthInsurerUpdate


def count_health_insurers(
    db: Session,
    *,
    is_active: bool | None = None,
) -> int:
    """Return the total number of health insurers.

    Useful for building ``PaginatedResponse`` in the router layer.
    Optionally filter by *is_active* status.
    """
    stmt = select(func.count()).select_from(HealthInsurer)
    if is_active is not None:
        stmt = stmt.where(HealthInsurer.is_active == is_active)
    return db.execute(stmt).scalar_one()


def list_health_insurers(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
) -> list[HealthInsurer]:
    """Return a paginated list of health insurers.

    Ordered by ``code`` ascending (24, 25, 27 …).
    Optionally filter by *is_active* status.
    """
    stmt = select(HealthInsurer).order_by(HealthInsurer.code)
    if is_active is not None:
        stmt = stmt.where(HealthInsurer.is_active == is_active)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_health_insurer(db: Session, insurer_id: UUID) -> HealthInsurer | None:
    """Return a single health insurer by primary key, or ``None``."""
    return db.get(HealthInsurer, insurer_id)


def create_health_insurer(
    db: Session,
    payload: HealthInsurerCreate,
) -> HealthInsurer:
    """Insert a new health insurer and flush (no commit)."""
    insurer = HealthInsurer(**payload.model_dump())
    db.add(insurer)
    db.flush()
    return insurer


def update_health_insurer(
    db: Session,
    insurer_id: UUID,
    payload: HealthInsurerUpdate,
) -> HealthInsurer | None:
    """Partially update an existing health insurer.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    """
    insurer = db.get(HealthInsurer, insurer_id)
    if insurer is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(insurer, field, value)

    db.flush()
    return insurer


def delete_health_insurer(db: Session, insurer_id: UUID) -> bool:
    """Delete a health insurer by primary key.

    Returns ``True`` if the row was deleted, ``False`` if not found.
    """
    insurer = db.get(HealthInsurer, insurer_id)
    if insurer is None:
        return False

    db.delete(insurer)
    db.flush()
    return True
