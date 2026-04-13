"""JournalEntry model — accounting journal entries generated from payroll.

Represents double-entry accounting records synced to NEX Ledger.
Each payroll generates multiple journal entry lines (debit/credit)
for wages, social/health insurance, tax, and net wage liabilities.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class JournalEntry(UUIDMixin, TimestampMixin, Base):
    """Accounting journal entry line generated from payroll data.

    Each approved payroll generates a set of journal entry lines
    representing the double-entry accounting for that payroll period.
    These entries are synced to NEX Ledger via the integration API.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('debit', 'credit')",
            name="ck_journal_entries_entry_type",
        ),
        CheckConstraint(
            "amount >= 0",
            name="ck_journal_entries_amount_positive",
        ),
        Index(
            "ix_journal_entries_tenant_period",
            "tenant_id",
            "period_year",
            "period_month",
        ),
        Index(
            "ix_journal_entries_payroll_id",
            "payroll_id",
        ),
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to owning tenant",
    )

    payroll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payrolls.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to source payroll record",
    )

    # -- Period --

    period_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Accounting period year",
    )

    period_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Accounting period month (1-12)",
    )

    # -- Accounting entry --

    entry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Journal entry date (last day of period)",
    )

    account_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Slovak chart of accounts code (e.g. 521, 331, 336, 342, 524)",
    )

    account_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Account name for display",
    )

    entry_type: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="Entry type: debit or credit",
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Entry amount (always positive)",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Entry description / narration",
    )

    # -- Sync tracking --

    sync_batch_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Batch identifier for grouping entries in a sync operation",
    )

    synced_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when entry was synced to NEX Ledger",
    )

    def __repr__(self) -> str:
        return (
            f"<JournalEntry(account={self.account_code!r}, "
            f"type={self.entry_type!r}, "
            f"amount={self.amount!r}, "
            f"period={self.period_year}/{self.period_month})>"
        )
