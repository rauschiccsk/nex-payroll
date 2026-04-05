"""Pydantic v2 schemas for HealthInsurer entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HealthInsurerCreate(BaseModel):
    """Schema for creating a new health insurer."""

    code: str = Field(
        ...,
        max_length=4,
        examples=["25"],
        description="Insurer code (e.g. 24, 25, 27)",
    )
    name: str = Field(
        ...,
        max_length=200,
        examples=["Všeobecná zdravotná poisťovňa, a.s."],
        description="Full name of the health insurance company",
    )
    iban: str = Field(
        ...,
        max_length=34,
        examples=["SK8975000000000012345678"],
        description="IBAN of the insurer for payment orders",
    )
    bic: str | None = Field(
        default=None,
        max_length=11,
        description="BIC/SWIFT code; null if domestic-only",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the insurer is currently active",
    )


class HealthInsurerUpdate(BaseModel):
    """Schema for updating a health insurer.

    All fields optional — only supplied fields are updated.
    """

    code: str | None = Field(
        default=None,
        max_length=4,
    )
    name: str | None = Field(
        default=None,
        max_length=200,
    )
    iban: str | None = Field(
        default=None,
        max_length=34,
    )
    bic: str | None = Field(
        default=None,
        max_length=11,
    )
    is_active: bool | None = Field(
        default=None,
    )


class HealthInsurerRead(BaseModel):
    """Schema for returning a health insurer in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    iban: str
    bic: str | None
    is_active: bool
    created_at: datetime
