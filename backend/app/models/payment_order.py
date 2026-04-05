"""PaymentOrder model — payment instruction generated from payroll.

Schema: tenant-specific
Represents a single payment order (bank transfer) for wages, social/health
insurance contributions, tax advances, or pillar-2 savings.
"""

import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class PaymentOrder(UUIDMixin, TimestampMixin, Base):
    """Payment order belonging to a specific tenant.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Generated after payroll approval; groups payments by type (net wages,
    SP, ZP per insurer, tax, pillar-2).
    """

    __tablename__ = "payment_orders"
    __table_args__ = (
        CheckConstraint(
            "payment_type IN ("
            "'net_wage', 'sp', 'zp_vszp', 'zp_dovera', 'zp_union', "
            "'tax', 'pillar2')",
            name="ck_payment_orders_payment_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'exported', 'paid')",
            name="ck_payment_orders_status",
        ),
        Index(
            "ix_payment_orders_tenant_period_type",
            "tenant_id",
            "period_year",
            "period_month",
            "payment_type",
        ),
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        comment="Reference to owning tenant",
    )

    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
        nullable=True,
        comment="Reference to employee (for net_wage type)",
    )

    health_insurer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared.health_insurers.id"),
        nullable=True,
        comment="Reference to health insurer (for zp types)",
    )

    # -- Period --

    period_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Payroll period year",
    )

    period_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Payroll period month (1-12)",
    )

    # -- Payment details --

    payment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Type: net_wage, sp, zp_vszp, zp_dovera, zp_union, tax, pillar2",
    )

    recipient_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Recipient (beneficiary) name",
    )

    recipient_iban: Mapped[str] = mapped_column(
        String(34),
        nullable=False,
        comment="Recipient IBAN",
    )

    recipient_bic: Mapped[str | None] = mapped_column(
        String(11),
        nullable=True,
        comment="Recipient BIC/SWIFT code",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Payment amount in EUR",
    )

    # -- Bank symbols --

    variable_symbol: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Variable symbol for bank transfer",
    )

    specific_symbol: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Specific symbol for bank transfer",
    )

    constant_symbol: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
        comment="Constant symbol for bank transfer",
    )

    reference: Mapped[str | None] = mapped_column(
        String(140),
        nullable=True,
        comment="SEPA end-to-end reference",
    )

    # -- Status --

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="'pending'",
        comment="Order status: pending, exported, paid",
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentOrder(type={self.payment_type!r}, "
            f"amount={self.amount!r}, "
            f"status={self.status!r})>"
        )
