"""Pydantic v2 schemas for StatutoryDeadline entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

_DEADLINE_TYPE = Literal[
    "sp_monthly",
    "zp_monthly",
    "tax_advance",
    "tax_reconciliation",
    "sp_annual",
    "zp_annual",
]


class StatutoryDeadlineCreate(BaseModel):
    """Schema for creating a new statutory deadline."""

    deadline_type: _DEADLINE_TYPE = Field(
        ...,
        description="Deadline category: sp_monthly, zp_monthly, tax_advance, tax_reconciliation, sp_annual, zp_annual",
        examples=["sp_monthly"],
    )
    institution: str = Field(
        ...,
        max_length=100,
        examples=["Sociálna poisťovňa"],
        description="Target institution (e.g. Sociálna poisťovňa, VšZP, DÚ)",
    )
    day_of_month: int = Field(
        ...,
        ge=1,
        le=31,
        examples=[20],
        description="Day of month the deadline falls on",
    )
    description: str = Field(
        ...,
        examples=["Mesačný výkaz poistného a príspevkov"],
        description="Human-readable description (Slovak)",
    )
    valid_from: date = Field(
        ...,
        description="Start of validity period (inclusive)",
    )
    valid_to: date | None = Field(
        default=None,
        description="End of validity period (inclusive); null if open-ended",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the deadline is currently active",
    )


class StatutoryDeadlineUpdate(BaseModel):
    """Schema for updating a statutory deadline.

    All fields optional — only supplied fields are updated.
    """

    deadline_type: _DEADLINE_TYPE | None = Field(
        default=None,
    )
    institution: str | None = Field(
        default=None,
        max_length=100,
    )
    day_of_month: int | None = Field(
        default=None,
        ge=1,
        le=31,
    )
    description: str | None = Field(
        default=None,
    )
    valid_from: date | None = Field(
        default=None,
    )
    valid_to: date | None = Field(
        default=None,
    )
    is_active: bool | None = Field(
        default=None,
    )


class StatutoryDeadlineRead(BaseModel):
    """Schema for returning a statutory deadline in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deadline_type: _DEADLINE_TYPE
    institution: str
    day_of_month: int
    description: str
    valid_from: date
    valid_to: date | None
    is_active: bool
    created_at: datetime
