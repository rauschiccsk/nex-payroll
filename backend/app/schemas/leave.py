"""Pydantic v2 schemas for Leave entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each record represents a single leave / absence period for one employee,
with a specific type, date range, and approval status.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_LEAVE_TYPE = Literal[
    "annual",
    "sick_employer",
    "sick_sp",
    "ocr",
    "maternity",
    "parental",
    "unpaid",
    "obstacle",
]

_LEAVE_STATUS = Literal["pending", "approved", "rejected", "cancelled"]


# ---------------------------------------------------------------------------
# LeaveCreate
# ---------------------------------------------------------------------------


class LeaveCreate(BaseModel):
    """Schema for creating a new leave / absence request."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    employee_id: UUID = Field(
        ...,
        description="Reference to employee (employees.id)",
    )
    leave_type: _LEAVE_TYPE = Field(
        ...,
        examples=["annual"],
        description=("Leave type: annual, sick_employer, sick_sp, ocr, maternity, parental, unpaid, obstacle"),
    )
    start_date: date = Field(
        ...,
        examples=["2025-07-01"],
        description="First day of leave",
    )
    end_date: date = Field(
        ...,
        examples=["2025-07-14"],
        description="Last day of leave",
    )
    business_days: int = Field(
        ...,
        ge=1,
        examples=[10],
        description="Number of business (working) days in the leave period",
    )
    note: str | None = Field(
        default=None,
        examples=["Rodinná dovolenka"],
        description="Optional note or reason for the leave request",
    )

    @model_validator(mode="after")
    def _check_date_range(self) -> "LeaveCreate":
        """Ensure end_date is not before start_date."""
        if self.end_date < self.start_date:
            msg = "end_date must not be before start_date"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# LeaveUpdate
# ---------------------------------------------------------------------------


class LeaveUpdate(BaseModel):
    """Schema for updating a leave record.

    All fields optional — only supplied fields are updated.
    """

    leave_type: _LEAVE_TYPE | None = Field(default=None)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    business_days: int | None = Field(default=None, ge=1)
    status: _LEAVE_STATUS | None = Field(default=None)
    note: str | None = Field(default=None)
    approved_by: UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None)

    @model_validator(mode="after")
    def _check_date_range(self) -> "LeaveUpdate":
        """When both dates supplied, end_date must not be before start_date."""
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            msg = "end_date must not be before start_date"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# LeaveRead
# ---------------------------------------------------------------------------


class LeaveRead(BaseModel):
    """Schema for returning a leave record in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    leave_type: _LEAVE_TYPE
    start_date: date
    end_date: date
    business_days: int
    status: _LEAVE_STATUS
    note: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
