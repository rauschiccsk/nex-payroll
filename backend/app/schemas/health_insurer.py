"""Pydantic v2 schemas for HealthInsurer entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Basic IBAN pattern: 2-letter country code + 2 check digits + up to 30 alphanumeric
_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$")
# BIC/SWIFT: 8 or 11 alphanumeric characters
_BIC_RE = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")


def _validate_iban(value: str) -> str:
    """Validate IBAN format (uppercase, no spaces, basic structure)."""
    cleaned = value.replace(" ", "").upper()
    if not _IBAN_RE.match(cleaned):
        msg = "Invalid IBAN format"
        raise ValueError(msg)
    return cleaned


def _validate_bic(value: str | None) -> str | None:
    """Validate BIC/SWIFT format if provided."""
    if value is None:
        return None
    cleaned = value.replace(" ", "").upper()
    if not _BIC_RE.match(cleaned):
        msg = "Invalid BIC/SWIFT format (must be 8 or 11 alphanumeric characters)"
        raise ValueError(msg)
    return cleaned


class HealthInsurerCreate(BaseModel):
    """Schema for creating a new health insurer."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=4,
        examples=["25"],
        description="Insurer code (e.g. 24, 25, 27)",
    )
    name: str = Field(
        ...,
        min_length=1,
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

    @field_validator("code")
    @classmethod
    def _code_must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            msg = "Insurer code must contain only digits"
            raise ValueError(msg)
        return v

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v.strip():
            msg = "Name must not be blank"
            raise ValueError(msg)
        return v.strip()

    @field_validator("iban")
    @classmethod
    def _validate_iban(cls, v: str) -> str:
        return _validate_iban(v)

    @field_validator("bic")
    @classmethod
    def _validate_bic(cls, v: str | None) -> str | None:
        return _validate_bic(v)


class HealthInsurerUpdate(BaseModel):
    """Schema for updating a health insurer.

    All fields optional — only supplied fields are updated.
    """

    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )
    name: str | None = Field(
        default=None,
        min_length=1,
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

    @field_validator("code")
    @classmethod
    def _code_must_be_digits(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            msg = "Insurer code must contain only digits"
            raise ValueError(msg)
        return v

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                msg = "Name must not be blank"
                raise ValueError(msg)
            return v.strip()
        return v

    @field_validator("iban")
    @classmethod
    def _validate_iban(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_iban(v)
        return v

    @field_validator("bic")
    @classmethod
    def _validate_bic(cls, v: str | None) -> str | None:
        return _validate_bic(v)


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
