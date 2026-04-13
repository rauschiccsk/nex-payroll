"""Service layer for NEX Ledger synchronisation.

Provides operations to sync payroll data to the NEX Ledger system
by managing the ``ledger_sync_status`` field on Payroll records.
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.payroll import Payroll

# ---------------------------------------------------------------------------
# Allowed ledger sync status transitions
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset({"pending"}),
    "pending": frozenset({"synced", "error"}),
    "synced": frozenset({"pending"}),  # allow re-sync
    "error": frozenset({"pending"}),  # allow retry
}


def _validate_transition(current: str | None, target: str) -> None:
    """Raise ``ValueError`` if transition from *current* to *target* is invalid."""
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise ValueError(
            f"Invalid ledger_sync_status transition: {current!r} -> {target!r}. "
            f"Allowed targets from {current!r}: {sorted(allowed)}"
        )


# ---------------------------------------------------------------------------
# get_sync_status — summary for a period
# ---------------------------------------------------------------------------


def get_sync_status(
    db: Session,
    *,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
) -> dict:
    """Return a summary of ledger sync statuses for all payrolls in a period.

    Returns a dict with keys: total, pending, synced, error, not_synced.
    """
    base = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.period_year == period_year,
        Payroll.period_month == period_month,
    )

    payrolls = list(db.execute(base).scalars().all())

    counts = {
        "total": len(payrolls),
        "pending": sum(1 for p in payrolls if p.ledger_sync_status == "pending"),
        "synced": sum(1 for p in payrolls if p.ledger_sync_status == "synced"),
        "error": sum(1 for p in payrolls if p.ledger_sync_status == "error"),
        "not_synced": sum(1 for p in payrolls if p.ledger_sync_status is None),
        "period_year": period_year,
        "period_month": period_month,
        "tenant_id": str(tenant_id),
    }
    return counts


# ---------------------------------------------------------------------------
# mark_for_sync — bulk mark approved payrolls as pending
# ---------------------------------------------------------------------------


def mark_for_sync(
    db: Session,
    *,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
) -> int:
    """Mark all approved payrolls for a period as ``pending`` for ledger sync.

    Only payrolls with ``status='approved'`` and ``ledger_sync_status IS NULL``
    are affected.  Returns the number of records updated.
    """
    stmt = (
        update(Payroll)
        .where(
            Payroll.tenant_id == tenant_id,
            Payroll.period_year == period_year,
            Payroll.period_month == period_month,
            Payroll.status == "approved",
            Payroll.ledger_sync_status.is_(None),
        )
        .values(ledger_sync_status="pending")
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount


# ---------------------------------------------------------------------------
# update_sync_status — single payroll
# ---------------------------------------------------------------------------


def update_sync_status(
    db: Session,
    *,
    payroll_id: UUID,
    new_status: str,
) -> Payroll:
    """Transition a single payroll's ``ledger_sync_status``.

    Validates the transition before applying.
    Raises ``ValueError`` if the payroll is not found or the transition is invalid.
    """
    payroll = db.get(Payroll, payroll_id)
    if payroll is None:
        raise ValueError(f"Payroll with id={payroll_id} not found")

    _validate_transition(payroll.ledger_sync_status, new_status)
    payroll.ledger_sync_status = new_status
    db.flush()
    return payroll


# ---------------------------------------------------------------------------
# bulk_update_sync_status — update all pending → synced/error
# ---------------------------------------------------------------------------


def bulk_update_sync_status(
    db: Session,
    *,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
    new_status: str,
) -> int:
    """Bulk update ledger_sync_status for all pending payrolls in a period.

    Typically used after a batch sync operation to mark all as 'synced'
    or 'error'.  Only affects records currently in 'pending' status.
    Returns the number of records updated.
    Raises ``ValueError`` if *new_status* is not valid for pending records.
    """
    _validate_transition("pending", new_status)

    stmt = (
        update(Payroll)
        .where(
            Payroll.tenant_id == tenant_id,
            Payroll.period_year == period_year,
            Payroll.period_month == period_month,
            Payroll.ledger_sync_status == "pending",
        )
        .values(ledger_sync_status=new_status)
    )
    result = db.execute(stmt)
    db.flush()
    return result.rowcount


# ---------------------------------------------------------------------------
# list_pending — list payrolls pending sync
# ---------------------------------------------------------------------------


def list_pending(
    db: Session,
    *,
    tenant_id: UUID,
    period_year: int | None = None,
    period_month: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Payroll]:
    """Return payrolls with ``ledger_sync_status='pending'``.

    Optionally filtered by period.
    """
    stmt = (
        select(Payroll)
        .where(
            Payroll.tenant_id == tenant_id,
            Payroll.ledger_sync_status == "pending",
        )
        .order_by(Payroll.period_year.desc(), Payroll.period_month.desc())
    )

    if period_year is not None:
        stmt = stmt.where(Payroll.period_year == period_year)
    if period_month is not None:
        stmt = stmt.where(Payroll.period_month == period_month)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def count_pending(
    db: Session,
    *,
    tenant_id: UUID,
    period_year: int | None = None,
    period_month: int | None = None,
) -> int:
    """Count payrolls with ``ledger_sync_status='pending'``."""
    stmt = (
        select(func.count())
        .select_from(Payroll)
        .where(
            Payroll.tenant_id == tenant_id,
            Payroll.ledger_sync_status == "pending",
        )
    )
    if period_year is not None:
        stmt = stmt.where(Payroll.period_year == period_year)
    if period_month is not None:
        stmt = stmt.where(Payroll.period_month == period_month)

    return db.execute(stmt).scalar_one()
