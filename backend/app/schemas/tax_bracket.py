"""Pydantic v2 schemas for TaxBracket entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaxBracketCreate(BaseModel):
    """Schema for creating a new tax bracket."""

    bracket_order: int = Field(
        ...,
        ge=1,
        examples=[1],
        description="Order of tax bracket (1=lowest rate first)",
    )
    min_amount: Decimal = Field(
        ...,
        max_digits=12,
        decimal_places=2,
        examples=[Decimal("0.00")],
        description="Minimum taxable income for this bracket",
    )
    max_amount: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="Maximum taxable income for this bracket; null if unlimited",
    )
    rate_percent: Decimal = Field(
        ...,
        max_digits=5,
        decimal_places=2,
        examples=[Decimal("19.00")],
        description="Tax rate in percent (e.g. 19.00, 25.00)",
    )
    nczd_annual: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        examples=[Decimal("5646.48")],
        description="Annual NČZD (nezdaniteľná časť základu dane)",
    )
    nczd_monthly: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=2,
        examples=[Decimal("470.54")],
        description="Monthly NČZD (1/12 of annual)",
    )
    nczd_reduction_threshold: Decimal = Field(
        ...,
        max_digits=12,
        decimal_places=2,
        examples=[Decimal("24952.06")],
        description="Income threshold above which NČZD is reduced",
    )
    nczd_reduction_formula: str = Field(
        ...,
        max_length=100,
        examples=["44.2 * ZM - ZD"],
        description="Formula for NČZD reduction (e.g. '44.2 * ZM - ZD')",
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
    def _check_valid_range(self) -> "TaxBracketCreate":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            msg = "valid_to must be >= valid_from"
            raise ValueError(msg)
        return self


class TaxBracketUpdate(BaseModel):
    """Schema for updating a tax bracket.

    All fields optional — only supplied fields are updated.
    """

    bracket_order: int | None = Field(
        default=None,
        ge=1,
    )
    min_amount: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
    )
    max_amount: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
    )
    rate_percent: Decimal | None = Field(
        default=None,
        max_digits=5,
        decimal_places=2,
    )
    nczd_annual: Decimal | None = Field(
        default=None,
        max_digits=10,
        decimal_places=2,
    )
    nczd_monthly: Decimal | None = Field(
        default=None,
        max_digits=10,
        decimal_places=2,
    )
    nczd_reduction_threshold: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
    )
    nczd_reduction_formula: str | None = Field(
        default=None,
        max_length=100,
    )
    valid_from: date | None = Field(
        default=None,
    )
    valid_to: date | None = Field(
        default=None,
    )


class TaxBracketRead(BaseModel):
    """Schema for returning a tax bracket in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bracket_order: int
    min_amount: Decimal
    max_amount: Decimal | None
    rate_percent: Decimal
    nczd_annual: Decimal
    nczd_monthly: Decimal
    nczd_reduction_threshold: Decimal
    nczd_reduction_formula: str
    valid_from: date
    valid_to: date | None
    created_at: datetime
