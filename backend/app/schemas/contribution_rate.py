"""Pydantic v2 schemas for ContributionRate entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContributionRateCreate(BaseModel):
    """Schema for creating a new contribution rate."""

    rate_type: str = Field(
        ...,
        max_length=50,
        examples=["sp_employee_nemocenske"],
        description="Rate identifier, e.g. sp_employee_nemocenske, zp_employee",
    )
    rate_percent: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        examples=[Decimal("1.4000")],
        description="Contribution rate as percentage (e.g. 1.4000 = 1.4 %)",
    )
    max_assessment_base: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="Maximum assessment base; null if uncapped",
    )
    payer: Literal["employee", "employer"] = Field(
        ...,
        description="Who pays: employee or employer",
    )
    fund: str = Field(
        ...,
        max_length=50,
        examples=["nemocenske"],
        description="Insurance fund name",
    )
    valid_from: date = Field(
        ...,
        description="Start of validity period (inclusive)",
    )
    valid_to: date | None = Field(
        default=None,
        description="End of validity period (inclusive); null if open-ended",
    )


class ContributionRateUpdate(BaseModel):
    """Schema for updating a contribution rate.

    All fields optional — only supplied fields are updated.
    """

    rate_type: str | None = Field(
        default=None,
        max_length=50,
    )
    rate_percent: Decimal | None = Field(
        default=None,
        max_digits=6,
        decimal_places=4,
    )
    max_assessment_base: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
    )
    payer: Literal["employee", "employer"] | None = Field(
        default=None,
    )
    fund: str | None = Field(
        default=None,
        max_length=50,
    )
    valid_from: date | None = Field(
        default=None,
    )
    valid_to: date | None = Field(
        default=None,
    )


class ContributionRateRead(BaseModel):
    """Schema for returning a contribution rate in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rate_type: str
    rate_percent: Decimal
    max_assessment_base: Decimal | None
    payer: Literal["employee", "employer"]
    fund: str
    valid_from: date
    valid_to: date | None
    created_at: datetime
