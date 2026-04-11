"""Pydantic v2 schemas for StatutoryDeadline entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

_DEADLINE_TYPE = Literal[
    "monthly",
    "annual",
    "one_time",
]


class StatutoryDeadlineCreate(BaseModel):
    """Schema for creating a new statutory deadline."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        examples=["SP_MONTHLY"],
        description="Unique code identifier (e.g. SP_MONTHLY, ZP_MONTHLY)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Mesačný výkaz SP"],
        description="Human-readable name",
    )
    description: str | None = Field(
        default=None,
        description="Optional longer description (Slovak)",
    )
    deadline_type: _DEADLINE_TYPE = Field(
        ...,
        description="Deadline category: monthly, annual, one_time",
        examples=["monthly"],
    )
    day_of_month: int | None = Field(
        default=None,
        ge=1,
        le=31,
        examples=[20],
        description="Day of month the deadline falls on (NULL if not applicable)",
    )
    month_of_year: int | None = Field(
        default=None,
        ge=1,
        le=12,
        examples=[4],
        description="Month of year for annual deadlines (1-12, NULL for monthly)",
    )
    business_days_rule: bool = Field(
        default=False,
        description="If true, deadline shifts to next business day",
    )
    institution: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Sociálna poisťovňa"],
        description="Target institution (e.g. Sociálna poisťovňa, VšZP, DÚ)",
    )
    valid_from: date = Field(
        ...,
        description="Start of validity period (inclusive)",
    )
    valid_to: date | None = Field(
        default=None,
        description="End of validity period (inclusive); null if open-ended",
    )

    @model_validator(mode="after")
    def _check_valid_range(self) -> "StatutoryDeadlineCreate":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            msg = "valid_to must be >= valid_from"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_monthly_requires_day(self) -> "StatutoryDeadlineCreate":
        if self.deadline_type == "monthly" and self.day_of_month is None:
            msg = "day_of_month is required for monthly deadlines"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _check_annual_requires_month(self) -> "StatutoryDeadlineCreate":
        if self.deadline_type == "annual" and self.month_of_year is None:
            msg = "month_of_year is required for annual deadlines"
            raise ValueError(msg)
        return self


class StatutoryDeadlineUpdate(BaseModel):
    """Schema for updating a statutory deadline.

    All fields optional — only supplied fields are updated.
    """

    code: str | None = Field(
        default=None,
        max_length=50,
    )
    name: str | None = Field(
        default=None,
        max_length=200,
    )
    description: str | None = Field(
        default=None,
    )
    deadline_type: _DEADLINE_TYPE | None = Field(
        default=None,
    )
    day_of_month: int | None = Field(
        default=None,
        ge=1,
        le=31,
    )
    month_of_year: int | None = Field(
        default=None,
        ge=1,
        le=12,
    )
    business_days_rule: bool | None = Field(
        default=None,
    )
    institution: str | None = Field(
        default=None,
        max_length=100,
    )
    valid_from: date | None = Field(
        default=None,
    )
    valid_to: date | None = Field(
        default=None,
    )


class StatutoryDeadlineRead(BaseModel):
    """Schema for returning a statutory deadline in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    deadline_type: _DEADLINE_TYPE
    day_of_month: int | None
    month_of_year: int | None
    business_days_rule: bool
    institution: str
    valid_from: date
    valid_to: date | None
    created_at: datetime
