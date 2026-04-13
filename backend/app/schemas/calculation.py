"""Pydantic v2 schemas for payroll calculation engine.

Input schema for triggering calculation, output schema for the result.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PayrollCalculateRequest(BaseModel):
    """Request body for triggering payroll calculation.

    Provides the gross wage components and period info.
    The engine fetches employee/contract/rates from DB.
    """

    tenant_id: UUID = Field(..., description="Tenant owning the payroll")
    employee_id: UUID = Field(..., description="Employee to calculate for")
    contract_id: UUID = Field(..., description="Active contract to use")
    period_year: int = Field(..., ge=2000, le=2100, description="Payroll year")
    period_month: int = Field(..., ge=1, le=12, description="Payroll month (1-12)")

    # Gross wage components (caller supplies these)
    overtime_hours: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=6,
        decimal_places=2,
        description="Overtime hours worked",
    )
    overtime_amount: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Overtime pay amount",
    )
    bonus_amount: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Bonus amount for the period",
    )
    supplement_amount: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Supplementary pay (night, weekend, holiday)",
    )


class ChildBonusDetail(BaseModel):
    """Detail of child tax bonus calculation for a single child."""

    model_config = ConfigDict(from_attributes=True)

    child_id: UUID
    child_name: str
    age: int
    bonus_amount: Decimal = Field(description="Individual child bonus (100€ or 50€)")


class PayrollCalculationResult(BaseModel):
    """Complete result of the gross-to-net payroll calculation.

    Mirrors all numeric fields on the Payroll model.
    """

    model_config = ConfigDict(from_attributes=True)

    # -- Gross wage --
    base_wage: Decimal
    overtime_hours: Decimal
    overtime_amount: Decimal
    bonus_amount: Decimal
    supplement_amount: Decimal
    gross_wage: Decimal

    # -- SP Employee (9.4%) --
    sp_assessment_base: Decimal
    sp_nemocenske: Decimal
    sp_starobne: Decimal
    sp_invalidne: Decimal
    sp_nezamestnanost: Decimal
    sp_employee_total: Decimal

    # -- ZP Employee --
    zp_assessment_base: Decimal
    zp_employee: Decimal

    # -- Tax --
    partial_tax_base: Decimal
    nczd_applied: Decimal
    tax_base: Decimal
    tax_advance: Decimal
    child_bonus: Decimal
    child_bonus_details: list[ChildBonusDetail] = Field(default_factory=list)
    tax_after_bonus: Decimal

    # -- Net --
    net_wage: Decimal

    # -- SP Employer --
    sp_employer_nemocenske: Decimal
    sp_employer_starobne: Decimal
    sp_employer_invalidne: Decimal
    sp_employer_nezamestnanost: Decimal
    sp_employer_garancne: Decimal
    sp_employer_rezervny: Decimal
    sp_employer_kurzarbeit: Decimal
    sp_employer_urazove: Decimal
    sp_employer_total: Decimal

    # -- ZP Employer --
    zp_employer: Decimal

    # -- Pillar 2 --
    pillar2_amount: Decimal

    # -- Total employer cost --
    total_employer_cost: Decimal

    # -- Metadata --
    period_year: int
    period_month: int
    employee_id: UUID
    contract_id: UUID
    effective_date: date
