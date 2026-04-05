"""Service layer for PaymentOrder entity.

Provides CRUD operations over the payment_orders table (tenant-specific schema).
All functions are synchronous (def, not async def) and accept a
SQLAlchemy Session.  They flush but never commit — the caller
(typically a FastAPI endpoint / unit-of-work) owns the transaction.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment_order import PaymentOrder
from app.schemas.payment_order import PaymentOrderCreate, PaymentOrderUpdate

ALLOWED_PAYMENT_TYPES = frozenset({"net_wage", "sp", "zp_vszp", "zp_dovera", "zp_union", "tax", "pillar2"})
ALLOWED_STATUSES = frozenset({"pending", "exported", "paid"})


def _validate_payment_type(value: str | None) -> None:
    """Raise ``ValueError`` if *value* is not a recognised payment_type."""
    if value is not None and value not in ALLOWED_PAYMENT_TYPES:
        raise ValueError(f"Invalid payment_type={value!r}. Allowed values: {sorted(ALLOWED_PAYMENT_TYPES)}")


def _validate_status(value: str | None) -> None:
    """Raise ``ValueError`` if *value* is not a recognised status."""
    if value is not None and value not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid status={value!r}. Allowed values: {sorted(ALLOWED_STATUSES)}")


def count_payment_orders(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    payment_type: str | None = None,
    status: str | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
) -> int:
    """Return the total number of payment orders matching the given filters.

    Useful for building ``PaginatedResponse`` in the router layer.
    """
    _validate_payment_type(payment_type)
    _validate_status(status)

    stmt = select(func.count()).select_from(PaymentOrder)

    if tenant_id is not None:
        stmt = stmt.where(PaymentOrder.tenant_id == tenant_id)

    if payment_type is not None:
        stmt = stmt.where(PaymentOrder.payment_type == payment_type)

    if status is not None:
        stmt = stmt.where(PaymentOrder.status == status)

    if period_year is not None:
        stmt = stmt.where(PaymentOrder.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(PaymentOrder.period_month == period_month)

    return db.execute(stmt).scalar_one()


def list_payment_orders(
    db: Session,
    *,
    tenant_id: UUID | None = None,
    payment_type: str | None = None,
    status: str | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[PaymentOrder]:
    """Return a paginated list of payment orders ordered by period (desc).

    When *tenant_id* is provided the result is scoped to that tenant.
    When *payment_type* is provided the result is filtered by type.
    When *status* is provided the result is filtered by status.
    When *period_year* / *period_month* are provided the result is filtered
    to the given period.
    """
    _validate_payment_type(payment_type)
    _validate_status(status)

    stmt = select(PaymentOrder).order_by(
        PaymentOrder.period_year.desc(),
        PaymentOrder.period_month.desc(),
    )

    if tenant_id is not None:
        stmt = stmt.where(PaymentOrder.tenant_id == tenant_id)

    if payment_type is not None:
        stmt = stmt.where(PaymentOrder.payment_type == payment_type)

    if status is not None:
        stmt = stmt.where(PaymentOrder.status == status)

    if period_year is not None:
        stmt = stmt.where(PaymentOrder.period_year == period_year)

    if period_month is not None:
        stmt = stmt.where(PaymentOrder.period_month == period_month)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_payment_order(db: Session, order_id: UUID) -> PaymentOrder | None:
    """Return a single payment order by primary key, or ``None``."""
    return db.get(PaymentOrder, order_id)


def create_payment_order(
    db: Session,
    payload: PaymentOrderCreate,
) -> PaymentOrder:
    """Insert a new payment order and flush (no commit).

    Validates *payment_type* and *status* at the service level before
    persisting.
    """
    _validate_payment_type(payload.payment_type)
    _validate_status(payload.status)

    order = PaymentOrder(**payload.model_dump())
    db.add(order)
    db.flush()
    return order


def update_payment_order(
    db: Session,
    order_id: UUID,
    payload: PaymentOrderUpdate,
) -> PaymentOrder:
    """Partially update an existing payment order.

    Only fields explicitly set in *payload* are changed.
    Raises ``ValueError`` if the order is not found.
    """
    update_data = payload.model_dump(exclude_unset=True)

    if "payment_type" in update_data:
        _validate_payment_type(update_data["payment_type"])
    if "status" in update_data:
        _validate_status(update_data["status"])

    order = db.get(PaymentOrder, order_id)
    if order is None:
        raise ValueError(f"PaymentOrder with id={order_id} not found")

    for field, value in update_data.items():
        setattr(order, field, value)

    db.flush()
    return order


def delete_payment_order(db: Session, order_id: UUID) -> None:
    """Delete a payment order by primary key (hard delete).

    Raises ``ValueError`` if the order is not found.
    """
    order = db.get(PaymentOrder, order_id)
    if order is None:
        raise ValueError(f"PaymentOrder with id={order_id} not found")

    db.delete(order)
    db.flush()
