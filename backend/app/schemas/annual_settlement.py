"""Pydantic v2 schemas for annual tax settlement.

Input/output schemas for annual tax settlement calculation,
income certificate generation, and annual tax report.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnnualSettlementRequest(BaseModel):
    """Request body for triggering annual tax settlement calculation."""

    tenant_id: UUID = Field(..., description="Tenant owning the employees")


class EmployeeSettlementResult(BaseModel):
    """Settlement result for a single employee."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    year: int

    # Annual income summary
    total_gross_wage: Decimal
    total_sp_employee: Decimal
    total_zp_employee: Decimal
    annual_partial_tax_base: Decimal

    # NCZD recalculation
    nczd_monthly_total: Decimal
    nczd_annual_recalculated: Decimal

    # Annual tax calculation
    annual_tax_base: Decimal
    annual_tax_19: Decimal
    annual_tax_25: Decimal
    annual_tax_total: Decimal
    annual_child_bonus: Decimal
    annual_tax_after_bonus: Decimal

    # Settlement
    total_monthly_advances: Decimal
    settlement_amount: Decimal
    months_count: int

    status: str
    calculated_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AnnualSettlementResponse(BaseModel):
    """Response for annual tax settlement calculation."""

    year: int
    tenant_id: UUID
    total_employees: int
    total_overpaid: Decimal = Field(description="Total refunds (positive)")
    total_underpaid: Decimal = Field(description="Total additional tax (negative)")
    settlements: list[EmployeeSettlementResult]


class AnnualTaxReportRequest(BaseModel):
    """Request body for generating annual tax report."""

    tenant_id: UUID = Field(..., description="Tenant owning the employees")


class AnnualTaxReportResponse(BaseModel):
    """Response for annual tax report generation."""

    year: int
    tenant_id: UUID
    total_employees: int
    total_gross_wages: Decimal
    total_tax_advances: Decimal
    total_annual_tax: Decimal
    total_settlement: Decimal
    report_generated: bool = True


class AnnualSettlementListResponse(BaseModel):
    """Response for listing annual settlements."""

    year: int
    tenant_id: UUID
    total_employees: int
    settlements: list[EmployeeSettlementResult]


class ApproveSettlementRequest(BaseModel):
    """Request body for approving an annual settlement."""

    tenant_id: UUID = Field(..., description="Tenant owning the settlement")
    approved_by: UUID = Field(..., description="User approving the settlement")


class ApproveSettlementResponse(BaseModel):
    """Response after approving an annual settlement."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    year: int
    status: str
    approved_at: datetime | None = None
    approved_by: UUID | None = None
    settlement_amount: Decimal
