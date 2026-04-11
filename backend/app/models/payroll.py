"""Payroll model — monthly wage calculation for an employee.

Schema: tenant-specific
Stores all components of monthly payroll calculation: gross wage,
social/health insurance contributions (employee + employer),
tax computation, and net wage. Supports full audit trail with
status workflow: draft → calculated → approved → paid.
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
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Payroll(UUIDMixin, TimestampMixin, Base):
    """Monthly payroll calculation for a single employee.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each record represents one month's complete wage computation,
    including gross components, social/health insurance contributions
    (both employee and employer shares), tax calculation, and net wage.
    """

    __tablename__ = "payrolls"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "employee_id",
            "period_year",
            "period_month",
            name="uq_payrolls_tenant_employee_period",
        ),
        CheckConstraint(
            "status IN ('draft', 'calculated', 'approved', 'paid')",
            name="ck_payrolls_status",
        ),
        CheckConstraint(
            "ledger_sync_status IN ('pending', 'synced', 'error')",
            name="ck_payrolls_ledger_sync_status",
        ),
        Index(
            "ix_payrolls_tenant_period_status",
            "tenant_id",
            "period_year",
            "period_month",
            "status",
        ),
        {"extend_existing": True},
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

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to active contract used for this payroll",
    )

    # -- Period --

    period_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Payroll period year (e.g. 2025)",
    )

    period_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Payroll period month (1-12)",
    )

    # -- Status --

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="draft",
        comment="Payroll status: draft, calculated, approved, paid",
    )

    # -- Gross wage components --

    base_wage: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Base wage from contract",
    )

    overtime_hours: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        server_default="0",
        comment="Number of overtime hours worked",
    )

    overtime_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
        comment="Overtime pay amount",
    )

    bonus_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
        comment="Bonus amount for the period",
    )

    supplement_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
        comment="Supplementary pay (night, weekend, holiday)",
    )

    gross_wage: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total gross wage (base + overtime + bonus + supplement)",
    )

    # -- Social insurance — employee contributions --

    sp_assessment_base: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Social insurance assessment base",
    )

    sp_nemocenske: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employee sickness insurance contribution",
    )

    sp_starobne: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employee old-age pension contribution",
    )

    sp_invalidne: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employee disability insurance contribution",
    )

    sp_nezamestnanost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employee unemployment insurance contribution",
    )

    sp_employee_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total employee social insurance contributions",
    )

    # -- Health insurance — employee contribution --

    zp_assessment_base: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Health insurance assessment base",
    )

    zp_employee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employee health insurance contribution",
    )

    # -- Tax calculation --

    partial_tax_base: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Partial tax base (gross - SP employee - ZP employee)",
    )

    nczd_applied: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Non-taxable amount (NČZD) applied",
    )

    tax_base: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Final tax base after NČZD deduction",
    )

    tax_advance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Advance income tax amount",
    )

    child_bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
        comment="Child tax bonus (daňový bonus na deti)",
    )

    tax_after_bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Tax after child bonus deduction",
    )

    # -- Net wage --

    net_wage: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Net wage paid to employee",
    )

    # -- Social insurance — employer contributions --

    sp_employer_nemocenske: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer sickness insurance contribution",
    )

    sp_employer_starobne: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer old-age pension contribution",
    )

    sp_employer_invalidne: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer disability insurance contribution",
    )

    sp_employer_nezamestnanost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer unemployment insurance contribution",
    )

    sp_employer_garancne: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer guarantee fund contribution",
    )

    sp_employer_rezervny: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer reserve fund contribution",
    )

    sp_employer_kurzarbeit: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer short-time work (kurzarbeit) contribution",
    )

    sp_employer_urazove: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer accident insurance contribution",
    )

    sp_employer_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total employer social insurance contributions",
    )

    zp_employer: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Employer health insurance contribution",
    )

    total_employer_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total employer cost (gross + SP employer + ZP employer)",
    )

    # -- Pillar 2 --

    pillar2_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
        comment="II. pillar pension saving deduction",
    )

    # -- AI validation --

    ai_validation_result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="AI validation result (anomalies, confidence score)",
    )

    # -- Ledger sync --

    ledger_sync_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Ledger synchronization status: pending, synced, error",
    )

    # -- Approval metadata --

    calculated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when payroll was calculated",
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when payroll was approved",
    )

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        comment="User who approved the payroll",
    )

    def __repr__(self) -> str:
        return (
            f"<Payroll(employee_id={self.employee_id!r}, "
            f"period={self.period_year}/{self.period_month}, "
            f"status={self.status!r}, "
            f"net_wage={self.net_wage!r})>"
        )
