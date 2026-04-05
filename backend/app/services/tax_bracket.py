"""Service layer for TaxBracket entity.

Provides CRUD operations over the shared.tax_brackets table.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session. They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tax_bracket import TaxBracket
from app.schemas.tax_bracket import TaxBracketCreate, TaxBracketUpdate


def count_tax_brackets(db: Session) -> int:
    """Return total number of tax brackets (for paginated responses)."""
    stmt = select(func.count()).select_from(TaxBracket)
    return db.execute(stmt).scalar_one()


def list_tax_brackets(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[TaxBracket]:
    """Return a paginated list of tax brackets.

    Ordered by ``valid_from`` descending then ``bracket_order`` ascending
    so the most-recent version appears first with brackets in logical order.
    """
    stmt = select(TaxBracket).order_by(TaxBracket.valid_from.desc(), TaxBracket.bracket_order).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_tax_bracket(db: Session, bracket_id: UUID) -> TaxBracket | None:
    """Return a single tax bracket by primary key, or ``None``."""
    return db.get(TaxBracket, bracket_id)


def create_tax_bracket(
    db: Session,
    payload: TaxBracketCreate,
) -> TaxBracket:
    """Insert a new tax bracket and flush (no commit).

    Raises ``ValueError`` if a bracket with the same ``(valid_from, bracket_order)``
    already exists (logical uniqueness).
    """
    duplicate_stmt = select(TaxBracket).where(
        TaxBracket.valid_from == payload.valid_from,
        TaxBracket.bracket_order == payload.bracket_order,
    )
    existing = db.execute(duplicate_stmt).scalar_one_or_none()
    if existing is not None:
        raise ValueError(
            f"Tax bracket with bracket_order={payload.bracket_order} and valid_from={payload.valid_from} already exists"
        )

    bracket = TaxBracket(**payload.model_dump())
    db.add(bracket)
    db.flush()
    return bracket


def update_tax_bracket(
    db: Session,
    bracket_id: UUID,
    payload: TaxBracketUpdate,
) -> TaxBracket | None:
    """Partially update an existing tax bracket.

    Only fields explicitly set in *payload* are changed.
    Returns the updated instance or ``None`` if not found.
    Raises ``ValueError`` if the update would create a duplicate
    ``(valid_from, bracket_order)`` combination.
    """
    bracket = db.get(TaxBracket, bracket_id)
    if bracket is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    # Check for duplicate (valid_from, bracket_order) if either field is being updated
    new_valid_from = update_data.get("valid_from", bracket.valid_from)
    new_bracket_order = update_data.get("bracket_order", bracket.bracket_order)
    if "valid_from" in update_data or "bracket_order" in update_data:
        duplicate_stmt = select(TaxBracket).where(
            TaxBracket.valid_from == new_valid_from,
            TaxBracket.bracket_order == new_bracket_order,
            TaxBracket.id != bracket_id,
        )
        existing = db.execute(duplicate_stmt).scalar_one_or_none()
        if existing is not None:
            raise ValueError(
                f"Tax bracket with bracket_order={new_bracket_order} and valid_from={new_valid_from} already exists"
            )

    for field, value in update_data.items():
        setattr(bracket, field, value)

    db.flush()
    return bracket


def delete_tax_bracket(db: Session, bracket_id: UUID) -> bool:
    """Delete a tax bracket by primary key.

    Returns ``True`` if the row was deleted, ``False`` if not found.
    Currently no FK dependencies reference tax_brackets.
    """
    bracket = db.get(TaxBracket, bracket_id)
    if bracket is None:
        return False

    db.delete(bracket)
    db.flush()
    return True
