"""Service layer for ContributionRate entity.

Provides CRUD operations over the shared.contribution_rates table.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session. They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.contribution_rate import ContributionRate
from app.schemas.contribution_rate import ContributionRateCreate, ContributionRateUpdate


def _apply_filters(
    stmt,
    *,
    rate_type: str | None = None,
    payer: str | None = None,
):
    """Apply optional filters to a ContributionRate query."""
    if rate_type is not None:
        stmt = stmt.where(ContributionRate.rate_type == rate_type)
    if payer is not None:
        stmt = stmt.where(ContributionRate.payer == payer)
    return stmt


def count_contribution_rates(
    db: Session,
    *,
    rate_type: str | None = None,
    payer: str | None = None,
) -> int:
    """Return the total number of contribution rates (with optional filters).

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    stmt = select(func.count()).select_from(ContributionRate)
    stmt = _apply_filters(stmt, rate_type=rate_type, payer=payer)
    return db.execute(stmt).scalar_one()


def list_contribution_rates(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    rate_type: str | None = None,
    payer: str | None = None,
) -> list[ContributionRate]:
    """Return a paginated list of contribution rates.

    Ordered by ``rate_type`` then ``valid_from`` descending so the
    most-recent version of each rate comes first.
    Supports optional filtering by ``rate_type`` and ``payer``.
    """
    stmt = select(ContributionRate)
    stmt = _apply_filters(stmt, rate_type=rate_type, payer=payer)
    stmt = stmt.order_by(ContributionRate.rate_type, ContributionRate.valid_from.desc())
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_contribution_rate(db: Session, rate_id: UUID) -> ContributionRate | None:
    """Return a single contribution rate by primary key, or ``None``."""
    return db.get(ContributionRate, rate_id)


def create_contribution_rate(
    db: Session,
    payload: ContributionRateCreate,
) -> ContributionRate:
    """Insert a new contribution rate and flush (no commit)."""
    rate = ContributionRate(**payload.model_dump())
    db.add(rate)
    db.flush()
    return rate


def update_contribution_rate(
    db: Session,
    rate_id: UUID,
    payload: ContributionRateUpdate,
) -> ContributionRate | None:
    """Partially update an existing contribution rate.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    """
    rate = db.get(ContributionRate, rate_id)
    if rate is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rate, field, value)

    db.flush()
    return rate


def delete_contribution_rate(db: Session, rate_id: UUID) -> bool:
    """Delete a contribution rate by primary key.

    Returns ``True`` if the row was deleted, ``False`` if not found.
    """
    rate = db.get(ContributionRate, rate_id)
    if rate is None:
        return False

    db.delete(rate)
    db.flush()
    return True
