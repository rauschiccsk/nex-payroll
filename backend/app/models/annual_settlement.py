"""AnnualSettlement model — annual tax settlement per employee.

Schema: tenant-specific
Stores the result of the annual tax recalculation comparing
actual annual tax (with NČZD recalculation) vs. sum of monthly advances.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AnnualSettlement(UUIDMixin, TimestampMixin, Base):
    """Annual tax settlement for a single employee.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each record represents the annual tax recalculation for one year,
    comparing the actual annual tax liability (using annual NČZD rules)
    against the sum of monthly tax advances paid during the year.

    A positive settlement_amount means the employee overpaid (refund).
    A negative settlement_amount means the employee underpaid (additional tax).
    """

    __tablename__ = "annual_settlements"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "employee_id",
            "year",
            name="uq_annual_settlements_tenant_employee_year",
        ),
        CheckConstraint(
            "status IN ('calculated', 'approved', 'paid')",
            name="ck_annual_settlements_status",
        ),
        Index(
            "ix_annual_settlements_tenant_year",
            "tenant_id",
            "year",
        ),
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to owning tenant",
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to employee",
    )

    # -- Period --

    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Settlement year (e.g. 2026)",
    )

    # -- Annual income summary --

    total_gross_wage: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total annual gross wage (sum of monthly gross wages)",
    )

    total_sp_employee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total annual SP employee contributions",
    )

    total_zp_employee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total annual ZP employee contributions",
    )

    annual_partial_tax_base: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Annual partial tax base (gross - SP - ZP)",
    )

    # -- NČZD recalculation --

    nczd_monthly_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Sum of monthly NČZD applied during the year",
    )

    nczd_annual_recalculated: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Recalculated annual NČZD using annual rules",
    )

    # -- Annual tax calculation --

    annual_tax_base: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Annual tax base (partial_tax_base - annual NČZD)",
    )

    annual_tax_19: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Tax at 19% rate (on amount up to threshold)",
    )

    annual_tax_25: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default="0",
        comment="Tax at 25% rate (on amount above threshold)",
    )

    annual_tax_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total annual tax liability (19% + 25%)",
    )

    annual_child_bonus: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        server_default="0",
        comment="Total annual child tax bonus",
    )

    annual_tax_after_bonus: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Annual tax after child bonus deduction",
    )

    # -- Settlement --

    total_monthly_advances: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Sum of monthly tax advances paid during the year",
    )

    settlement_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Settlement: positive=overpaid (refund), negative=underpaid",
    )

    months_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of payroll months included in settlement",
    )

    # -- Status --

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="calculated",
        comment="Settlement status: calculated, approved, paid",
    )

    calculated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when settlement was calculated",
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when settlement was approved",
    )

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who approved the settlement",
    )

    def __repr__(self) -> str:
        return (
            f"<AnnualSettlement(employee_id={self.employee_id!r}, "
            f"year={self.year}, "
            f"settlement_amount={self.settlement_amount!r}, "
            f"status={self.status!r})>"
        )
