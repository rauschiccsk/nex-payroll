"""Pydantic v2 schemas for LeaveEntitlement entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each employee has one entitlement record per calendar year, tracking total days,
used days, remaining days, and carryover from the previous year.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# LeaveEntitlementCreate
# ---------------------------------------------------------------------------


class LeaveEntitlementCreate(BaseModel):
    """Schema for creating a new annual leave entitlement record."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    employee_id: UUID = Field(
        ...,
        description="Reference to employee (employees.id)",
    )
    year: int = Field(
        ...,
        ge=2000,
        le=2100,
        examples=[2025],
        description="Calendar year of the entitlement",
    )
    total_days: int = Field(
        ...,
        ge=0,
        examples=[25],
        description="Total annual leave days entitled",
    )
    used_days: int = Field(
        default=0,
        ge=0,
        examples=[0],
        description="Number of leave days already used",
    )
    remaining_days: int = Field(
        ...,
        ge=0,
        examples=[25],
        description="Remaining leave days (computed: total - used)",
    )
    carryover_days: int = Field(
        default=0,
        ge=0,
        examples=[3],
        description="Leave days carried over from previous year",
    )

    @model_validator(mode="after")
    def _check_used_le_total(self) -> "LeaveEntitlementCreate":
        """Ensure used_days does not exceed total_days."""
        if self.used_days > self.total_days:
            msg = "used_days must not exceed total_days"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_remaining_consistency(self) -> "LeaveEntitlementCreate":
        """Ensure remaining_days equals total_days - used_days."""
        expected = self.total_days - self.used_days
        if self.remaining_days != expected:
            msg = f"remaining_days ({self.remaining_days}) must equal total_days - used_days ({expected})"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# LeaveEntitlementUpdate
# ---------------------------------------------------------------------------


class LeaveEntitlementUpdate(BaseModel):
    """Schema for updating a leave entitlement record.

    All fields optional — only supplied fields are updated.
    """

    total_days: int | None = Field(default=None, ge=0)
    used_days: int | None = Field(default=None, ge=0)
    remaining_days: int | None = Field(default=None, ge=0)
    carryover_days: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_used_le_total(self) -> "LeaveEntitlementUpdate":
        """When both supplied, used_days must not exceed total_days."""
        if self.used_days is not None and self.total_days is not None and self.used_days > self.total_days:
            msg = "used_days must not exceed total_days"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# LeaveEntitlementRead
# ---------------------------------------------------------------------------


class LeaveEntitlementRead(BaseModel):
    """Schema for returning a leave entitlement record in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    year: int
    total_days: int
    used_days: int
    remaining_days: int
    carryover_days: int
    created_at: datetime
    updated_at: datetime
