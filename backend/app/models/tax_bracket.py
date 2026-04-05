"""TaxBracket model — versioned income tax brackets.

Schema: shared
Stores progressive tax brackets with NČZD (non-taxable amount) rules.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class TaxBracket(UUIDMixin, Base):
    """Versioned income tax bracket definition.

    Lives in the 'shared' schema — shared across all tenants.
    Only created_at (no updated_at) — rates are immutable once created.

    Defines progressive tax brackets for Slovak income tax:
      - 19% bracket (up to 176.8× subsistence minimum)
      - 25% bracket (above threshold)
    Includes NČZD (nezdaniteľná časť základu dane) rules.
    """

    __tablename__ = "tax_brackets"
    __table_args__ = (
        Index("ix_tax_brackets_valid_from_bracket_order", "valid_from", "bracket_order"),
        {"schema": "shared"},
    )

    bracket_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Order of tax bracket (1=lowest rate first)",
    )

    min_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Minimum taxable income for this bracket",
    )

    max_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Maximum taxable income for this bracket (NULL=unlimited)",
    )

    rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Tax rate in percent (e.g. 19.00, 25.00)",
    )

    nczd_annual: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Annual NČZD (nezdaniteľná časť základu dane)",
    )

    nczd_monthly: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Monthly NČZD (1/12 of annual)",
    )

    nczd_reduction_threshold: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Income threshold above which NČZD is reduced",
    )

    nczd_reduction_formula: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Formula for NČZD reduction (e.g. '44.2 * ZM - ZD')",
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Only created_at — rates are immutable
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<TaxBracket(order={self.bracket_order}, "
            f"rate={self.rate_percent}%, "
            f"min={self.min_amount}, max={self.max_amount}, "
            f"valid_from={self.valid_from})>"
        )
