"""Pydantic v2 schemas for Leave entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each record represents a single leave / absence period for one employee,
with a specific type, date range, and approval status.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    status: _LEAVE_STATUS = Field(
        default="pending",
        examples=["pending"],
        description="Leave status: pending, approved, rejected, cancelled",
    )
    note: str | None = Field(
        default=None,
        examples=["Rodinná dovolenka"],
        description="Optional note or reason for the leave request",
    )
    approved_by: UUID | None = Field(
        default=None,
        description="User who approved/rejected the leave request",
    )
    approved_at: datetime | None = Field(
        default=None,
        description="Timestamp when the leave was approved/rejected",
    )


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


# ---------------------------------------------------------------------------
# LeaveRead
# ---------------------------------------------------------------------------


class LeaveRead(BaseModel):
    """Schema for returning a leave record in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    business_days: int
    status: str
    note: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
