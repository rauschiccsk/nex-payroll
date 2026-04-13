"""SEPA XML generator service — pain.001.001.03.

Generates SEPA Credit Transfer Initiation (pain.001.001.03) XML from
a list of PaymentOrder records.  Uses the ``sepaxml`` library.

All functions are synchronous (def, not async def).
"""

import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from sepaxml import SepaTransfer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_order import PaymentOrder
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

_CENTS_FACTOR = 100


def _amount_to_cents(amount: Decimal) -> int:
    """Convert EUR Decimal (12,2) to integer cents for sepaxml."""
    return int((amount * _CENTS_FACTOR).to_integral_value())


def _build_description(order: PaymentOrder) -> str:
    """Build unstructured remittance info for a single payment.

    Encodes Slovak bank symbols (VS, SS, KS) into the description field
    because SEPA XML does not have dedicated fields for them.
    """
    parts: list[str] = []
    if order.variable_symbol:
        parts.append(f"/VS{order.variable_symbol}")
    if order.specific_symbol:
        parts.append(f"/SS{order.specific_symbol}")
    if order.constant_symbol:
        parts.append(f"/KS{order.constant_symbol}")
    if not parts:
        return f"Payment {order.payment_type} {order.period_year}/{order.period_month:02d}"
    return "".join(parts)


def _build_end_to_end_id(order: PaymentOrder) -> str:
    """Build SEPA EndToEndId from the order's reference or generate one."""
    if order.reference:
        # SEPA EndToEndId max 35 chars
        return order.reference[:35]
    # Fallback: compact identifier
    short_id = str(order.id).replace("-", "")[:16]
    return f"PO-{short_id}"


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------


def generate_sepa_xml(
    db: Session,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
    execution_date: date | None = None,
) -> bytes:
    """Generate SEPA XML (pain.001.001.03) for all pending payment orders.

    Parameters
    ----------
    db : Session
        SQLAlchemy session (caller owns the transaction).
    tenant_id : UUID
        Owning tenant — debtor account is taken from the tenant record.
    period_year, period_month : int
        Payroll period to export.
    execution_date : date | None
        Requested execution date.  Defaults to today if not provided.

    Returns
    -------
    bytes
        UTF-8 encoded XML document.

    Raises
    ------
    ValueError
        If tenant not found, no pending orders exist, or tenant IBAN is missing.
    """
    # --- Resolve tenant (debtor) ---
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={tenant_id} not found")

    if not tenant.bank_iban:
        raise ValueError(f"Tenant '{tenant.name}' has no bank_iban configured")

    # --- Fetch pending orders for the period ---
    stmt = (
        select(PaymentOrder)
        .where(
            PaymentOrder.tenant_id == tenant_id,
            PaymentOrder.period_year == period_year,
            PaymentOrder.period_month == period_month,
            PaymentOrder.status == "pending",
        )
        .order_by(PaymentOrder.payment_type, PaymentOrder.recipient_name)
    )
    orders: list[PaymentOrder] = list(db.execute(stmt).scalars().all())

    if not orders:
        raise ValueError(f"No pending payment orders for tenant={tenant_id}, period={period_year}/{period_month:02d}")

    # --- Build SEPA document ---
    if execution_date is None:
        execution_date = date.today()

    config = {
        "name": tenant.name[:70],  # SEPA max 70 chars for name
        "IBAN": tenant.bank_iban,
        "BIC": tenant.bank_bic or "NOTPROVIDED",
        "batch": True,
        "currency": "EUR",
    }

    sepa = SepaTransfer(config, schema="pain.001.001.03")

    for order in orders:
        payment = {
            "name": order.recipient_name[:70],
            "IBAN": order.recipient_iban,
            "BIC": order.recipient_bic or "NOTPROVIDED",
            "amount": _amount_to_cents(order.amount),
            "execution_date": execution_date,
            "description": _build_description(order)[:140],
            "endtoend_id": _build_end_to_end_id(order),
        }
        sepa.add_payment(payment)

    xml_bytes: bytes = sepa.export(validate=True, pretty_print=True)

    # --- Mark orders as exported ---
    for order in orders:
        order.status = "exported"
    db.flush()

    logger.info(
        "Generated SEPA XML for tenant=%s period=%d/%02d: %d orders, %d bytes",
        tenant_id,
        period_year,
        period_month,
        len(orders),
        len(xml_bytes),
    )

    return xml_bytes


def generate_sepa_xml_preview(
    db: Session,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
    execution_date: date | None = None,
) -> bytes:
    """Generate SEPA XML without marking orders as exported.

    Same as ``generate_sepa_xml`` but does NOT change order status.
    Useful for preview/download before final export.
    """
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={tenant_id} not found")

    if not tenant.bank_iban:
        raise ValueError(f"Tenant '{tenant.name}' has no bank_iban configured")

    stmt = (
        select(PaymentOrder)
        .where(
            PaymentOrder.tenant_id == tenant_id,
            PaymentOrder.period_year == period_year,
            PaymentOrder.period_month == period_month,
            PaymentOrder.status.in_(["pending", "exported"]),
        )
        .order_by(PaymentOrder.payment_type, PaymentOrder.recipient_name)
    )
    orders: list[PaymentOrder] = list(db.execute(stmt).scalars().all())

    if not orders:
        raise ValueError(f"No payment orders for tenant={tenant_id}, period={period_year}/{period_month:02d}")

    if execution_date is None:
        execution_date = date.today()

    config = {
        "name": tenant.name[:70],
        "IBAN": tenant.bank_iban,
        "BIC": tenant.bank_bic or "NOTPROVIDED",
        "batch": True,
        "currency": "EUR",
    }

    sepa = SepaTransfer(config, schema="pain.001.001.03")

    for order in orders:
        payment = {
            "name": order.recipient_name[:70],
            "IBAN": order.recipient_iban,
            "BIC": order.recipient_bic or "NOTPROVIDED",
            "amount": _amount_to_cents(order.amount),
            "execution_date": execution_date,
            "description": _build_description(order)[:140],
            "endtoend_id": _build_end_to_end_id(order),
        }
        sepa.add_payment(payment)

    return sepa.export(validate=True, pretty_print=True)
