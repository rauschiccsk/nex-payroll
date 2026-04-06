"""Pydantic v2 schemas for Contract entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_CONTRACT_TYPE = Literal["permanent", "fixed_term", "agreement_work", "agreement_activity"]
_WAGE_TYPE = Literal["monthly", "hourly"]


# ---------------------------------------------------------------------------
# ContractCreate
# ---------------------------------------------------------------------------


class ContractCreate(BaseModel):
    """Schema for creating a new employment contract."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    employee_id: UUID = Field(
        ...,
        description="Reference to employee (employees.id)",
    )
    contract_number: str = Field(
        ...,
        max_length=50,
        examples=["PZ-2024-001"],
        description="Unique contract number within tenant",
    )
    contract_type: _CONTRACT_TYPE = Field(
        ...,
        examples=["permanent"],
        description="Contract type: permanent, fixed_term, agreement_work, agreement_activity",
    )
    job_title: str = Field(
        ...,
        max_length=200,
        examples=["Softvérový inžinier"],
        description="Job position title",
    )
    wage_type: _WAGE_TYPE = Field(
        ...,
        examples=["monthly"],
        description="Wage type: monthly or hourly",
    )
    base_wage: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        examples=["2500.00"],
        description="Base wage amount (monthly or hourly rate)",
    )
    hours_per_week: Decimal = Field(
        default=Decimal("40.0"),
        max_digits=4,
        decimal_places=1,
        examples=["40.0"],
        description="Contracted weekly working hours",
    )
    start_date: date = Field(
        ...,
        examples=["2024-01-15"],
        description="Contract start date",
    )
    end_date: date | None = Field(
        default=None,
        examples=["2025-12-31"],
        description="Contract end date (null for indefinite contracts)",
    )
    probation_end_date: date | None = Field(
        default=None,
        examples=["2024-04-15"],
        description="End date of probation period",
    )
    termination_date: date | None = Field(
        default=None,
        description="Actual termination date (null if not terminated)",
    )
    termination_reason: str | None = Field(
        default=None,
        max_length=200,
        description="Reason for contract termination",
    )
    is_current: bool = Field(
        default=True,
        description="Whether this is the currently active contract",
    )


# ---------------------------------------------------------------------------
# ContractUpdate
# ---------------------------------------------------------------------------


class ContractUpdate(BaseModel):
    """Schema for updating a contract.

    All fields optional — only supplied fields are updated.
    """

    contract_number: str | None = Field(default=None, max_length=50)
    contract_type: _CONTRACT_TYPE | None = Field(default=None)
    job_title: str | None = Field(default=None, max_length=200)
    wage_type: _WAGE_TYPE | None = Field(default=None)
    base_wage: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    hours_per_week: Decimal | None = Field(default=None, max_digits=4, decimal_places=1)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    probation_end_date: date | None = Field(default=None)
    termination_date: date | None = Field(default=None)
    termination_reason: str | None = Field(default=None, max_length=200)
    is_current: bool | None = Field(default=None)


# ---------------------------------------------------------------------------
# ContractRead
# ---------------------------------------------------------------------------


class ContractRead(BaseModel):
    """Schema for returning a contract in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    contract_number: str
    contract_type: str
    job_title: str
    wage_type: str
    base_wage: Decimal
    hours_per_week: Decimal
    start_date: date
    end_date: date | None
    probation_end_date: date | None
    termination_date: date | None
    termination_reason: str | None
    is_current: bool
    created_at: datetime
    updated_at: datetime
