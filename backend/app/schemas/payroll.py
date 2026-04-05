"""Pydantic v2 schemas for Payroll entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_STATUS = Literal["draft", "calculated", "approved", "paid"]
_LEDGER_SYNC_STATUS = Literal["pending", "synced", "error"]


# ---------------------------------------------------------------------------
# PayrollCreate
# ---------------------------------------------------------------------------


class PayrollCreate(BaseModel):
    """Schema for creating a new monthly payroll record."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    employee_id: UUID = Field(
        ...,
        description="Reference to employee (employees.id)",
    )
    contract_id: UUID = Field(
        ...,
        description="Reference to active contract used for this payroll",
    )
    period_year: int = Field(
        ...,
        examples=[2025],
        description="Payroll period year (e.g. 2025)",
    )
    period_month: int = Field(
        ...,
        ge=1,
        le=12,
        examples=[1],
        description="Payroll period month (1-12)",
    )
    status: _STATUS = Field(
        default="draft",
        examples=["draft"],
        description="Payroll status: draft, calculated, approved, paid",
    )

    # -- Gross wage components --
    base_wage: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        examples=["2500.00"],
        description="Base wage from contract",
    )
    overtime_hours: Decimal = Field(
        default=Decimal("0"),
        max_digits=6,
        decimal_places=2,
        examples=["0.00"],
        description="Number of overtime hours worked",
    )
    overtime_amount: Decimal = Field(
        default=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        examples=["0.00"],
        description="Overtime pay amount",
    )
    bonus_amount: Decimal = Field(
        default=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        examples=["0.00"],
        description="Bonus amount for the period",
    )
    supplement_amount: Decimal = Field(
        default=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        examples=["0.00"],
        description="Supplementary pay (night, weekend, holiday)",
    )
    gross_wage: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        examples=["2500.00"],
        description="Total gross wage (base + overtime + bonus + supplement)",
    )

    # -- Social insurance — employee contributions --
    sp_assessment_base: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Social insurance assessment base",
    )
    sp_nemocenske: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employee sickness insurance contribution",
    )
    sp_starobne: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employee old-age pension contribution",
    )
    sp_invalidne: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employee disability insurance contribution",
    )
    sp_nezamestnanost: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employee unemployment insurance contribution",
    )
    sp_employee_total: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Total employee social insurance contributions",
    )

    # -- Health insurance — employee contribution --
    zp_assessment_base: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Health insurance assessment base",
    )
    zp_employee: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employee health insurance contribution",
    )

    # -- Tax calculation --
    partial_tax_base: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Partial tax base (gross - SP employee - ZP employee)",
    )
    nczd_applied: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Non-taxable amount (NČZD) applied",
    )
    tax_base: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Final tax base after NČZD deduction",
    )
    tax_advance: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Advance income tax amount",
    )
    child_bonus: Decimal = Field(
        default=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        examples=["0.00"],
        description="Child tax bonus (daňový bonus na deti)",
    )
    tax_after_bonus: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Tax after child bonus deduction",
    )

    # -- Net wage --
    net_wage: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        examples=["1850.75"],
        description="Net wage paid to employee",
    )

    # -- Social insurance — employer contributions --
    sp_employer_nemocenske: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer sickness insurance contribution",
    )
    sp_employer_starobne: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer old-age pension contribution",
    )
    sp_employer_invalidne: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer disability insurance contribution",
    )
    sp_employer_nezamestnanost: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer unemployment insurance contribution",
    )
    sp_employer_garancne: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer guarantee fund contribution",
    )
    sp_employer_rezervny: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer reserve fund contribution",
    )
    sp_employer_kurzarbeit: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer short-time work (kurzarbeit) contribution",
    )
    sp_employer_urazove: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer accident insurance contribution",
    )
    sp_employer_total: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Total employer social insurance contributions",
    )
    zp_employer: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Employer health insurance contribution",
    )
    total_employer_cost: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        description="Total employer cost (gross + SP employer + ZP employer)",
    )

    # -- Pillar 2 --
    pillar2_amount: Decimal = Field(
        default=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        examples=["0.00"],
        description="II. pillar pension saving deduction",
    )


# ---------------------------------------------------------------------------
# PayrollUpdate
# ---------------------------------------------------------------------------


class PayrollUpdate(BaseModel):
    """Schema for updating a payroll record.

    All fields optional — only supplied fields are updated.
    """

    status: _STATUS | None = Field(default=None)

    # -- Gross wage components --
    base_wage: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    overtime_hours: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    overtime_amount: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    bonus_amount: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    supplement_amount: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    gross_wage: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # -- Social insurance — employee contributions --
    sp_assessment_base: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_nemocenske: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_starobne: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_invalidne: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_nezamestnanost: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employee_total: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # -- Health insurance — employee contribution --
    zp_assessment_base: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    zp_employee: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # -- Tax calculation --
    partial_tax_base: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    nczd_applied: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    tax_base: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    tax_advance: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    child_bonus: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    tax_after_bonus: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # -- Net wage --
    net_wage: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # -- Social insurance — employer contributions --
    sp_employer_nemocenske: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_starobne: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_invalidne: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_nezamestnanost: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_garancne: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_rezervny: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_kurzarbeit: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_urazove: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    sp_employer_total: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    zp_employer: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    total_employer_cost: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # -- Pillar 2 --
    pillar2_amount: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)

    # -- AI validation --
    ai_validation_result: dict[str, Any] | None = Field(default=None)

    # -- Ledger sync --
    ledger_sync_status: _LEDGER_SYNC_STATUS | None = Field(default=None)

    # -- Approval metadata --
    calculated_at: datetime | None = Field(default=None)
    approved_at: datetime | None = Field(default=None)
    approved_by: UUID | None = Field(default=None)


# ---------------------------------------------------------------------------
# PayrollRead
# ---------------------------------------------------------------------------


class PayrollRead(BaseModel):
    """Schema for returning a payroll record in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    contract_id: UUID
    period_year: int
    period_month: int
    status: str

    # -- Gross wage components --
    base_wage: Decimal
    overtime_hours: Decimal
    overtime_amount: Decimal
    bonus_amount: Decimal
    supplement_amount: Decimal
    gross_wage: Decimal

    # -- Social insurance — employee contributions --
    sp_assessment_base: Decimal
    sp_nemocenske: Decimal
    sp_starobne: Decimal
    sp_invalidne: Decimal
    sp_nezamestnanost: Decimal
    sp_employee_total: Decimal

    # -- Health insurance — employee contribution --
    zp_assessment_base: Decimal
    zp_employee: Decimal

    # -- Tax calculation --
    partial_tax_base: Decimal
    nczd_applied: Decimal
    tax_base: Decimal
    tax_advance: Decimal
    child_bonus: Decimal
    tax_after_bonus: Decimal

    # -- Net wage --
    net_wage: Decimal

    # -- Social insurance — employer contributions --
    sp_employer_nemocenske: Decimal
    sp_employer_starobne: Decimal
    sp_employer_invalidne: Decimal
    sp_employer_nezamestnanost: Decimal
    sp_employer_garancne: Decimal
    sp_employer_rezervny: Decimal
    sp_employer_kurzarbeit: Decimal
    sp_employer_urazove: Decimal
    sp_employer_total: Decimal
    zp_employer: Decimal
    total_employer_cost: Decimal

    # -- Pillar 2 --
    pillar2_amount: Decimal

    # -- AI validation --
    ai_validation_result: dict[str, Any] | None

    # -- Ledger sync --
    ledger_sync_status: str | None

    # -- Approval metadata --
    calculated_at: datetime | None
    approved_at: datetime | None
    approved_by: UUID | None

    # -- Timestamps --
    created_at: datetime
    updated_at: datetime
