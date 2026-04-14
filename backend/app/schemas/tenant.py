"""Pydantic v2 schemas for Tenant entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Provides TenantBase, TenantCreate, TenantUpdate, TenantInDB (full DB read),
and TenantPublic (safe subset for API responses).
"""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# Basic IBAN pattern: 2-letter country code + 2 check digits + up to 30 alphanumeric
_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$")
# BIC/SWIFT: 8 or 11 alphanumeric characters
_BIC_RE = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")
# IČO: exactly 8 digits
_ICO_RE = re.compile(r"^\d{8}$")
# DIČ: 10-12 digits
_DIC_RE = re.compile(r"^\d{10,12}$")
# IČ DPH: SK + 10 digits
_IC_DPH_RE = re.compile(r"^SK\d{10}$")
# ISO 3166-1 alpha-2 country code
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
# PostgreSQL schema name for tenants
_SCHEMA_NAME_RE = re.compile(r"^tenant_[a-z0-9_]+$")


# ---------------------------------------------------------------------------
# Shared validation helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TenantBase — shared writable fields
# ---------------------------------------------------------------------------


class TenantBase(BaseModel):
    """Common fields shared between Create and Read schemas."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Firma s.r.o."],
        description="Company name",
    )
    ico: str = Field(
        ...,
        max_length=8,
        examples=["12345678"],
        description="IČO — company identification number (8 digits)",
    )
    dic: str | None = Field(
        default=None,
        max_length=12,
        examples=["2012345678"],
        description="DIČ — tax identification number",
    )
    ic_dph: str | None = Field(
        default=None,
        max_length=14,
        examples=["SK2012345678"],
        description="IČ DPH — VAT identification number",
    )
    address_street: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Hlavná 1"],
        description="Street address",
    )
    address_city: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Bratislava"],
        description="City",
    )
    address_zip: str = Field(
        ...,
        min_length=1,
        max_length=10,
        examples=["81101"],
        description="Postal / ZIP code",
    )
    address_country: str = Field(
        default="SK",
        max_length=2,
        examples=["SK"],
        description="ISO 3166-1 alpha-2 country code",
    )
    bank_iban: str = Field(
        ...,
        max_length=34,
        examples=["SK8975000000000012345678"],
        description="Company bank account IBAN",
    )
    bank_bic: str | None = Field(
        default=None,
        max_length=11,
        description="BIC/SWIFT code; null if domestic-only",
    )

    # -- validators --

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v.strip():
            msg = "Name must not be blank"
            raise ValueError(msg)
        return v.strip()

    @field_validator("ico")
    @classmethod
    def _ico_must_be_8_digits(cls, v: str) -> str:
        if not _ICO_RE.match(v):
            msg = "IČO must be exactly 8 digits"
            raise ValueError(msg)
        return v

    @field_validator("dic")
    @classmethod
    def _dic_format(cls, v: str | None) -> str | None:
        if v is not None and not _DIC_RE.match(v):
            msg = "DIČ must be 10-12 digits"
            raise ValueError(msg)
        return v

    @field_validator("ic_dph")
    @classmethod
    def _ic_dph_format(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.upper()
            if not _IC_DPH_RE.match(cleaned):
                msg = "IČ DPH must match format SK + 10 digits (e.g. SK2012345678)"
                raise ValueError(msg)
            return cleaned
        return v

    @field_validator("address_country")
    @classmethod
    def _country_code_format(cls, v: str) -> str:
        cleaned = v.upper()
        if not _COUNTRY_RE.match(cleaned):
            msg = "Country must be a 2-letter ISO 3166-1 alpha-2 code"
            raise ValueError(msg)
        return cleaned

    @field_validator("bank_iban")
    @classmethod
    def _validate_iban(cls, v: str) -> str:
        return _validate_iban(v)

    @field_validator("bank_bic")
    @classmethod
    def _validate_bic(cls, v: str | None) -> str | None:
        return _validate_bic(v)


# ---------------------------------------------------------------------------
# TenantCreate
# ---------------------------------------------------------------------------


class TenantCreate(TenantBase):
    """Schema for creating a new tenant (company).

    Inherits all base fields + adds schema_name, default_role, is_active.
    """

    schema_name: str | None = Field(
        default=None,
        max_length=63,
        examples=["tenant_firma"],
        description=(
            "PostgreSQL schema name (must match ^tenant_[a-z0-9_]+$). Auto-generated from name + IČO if not provided."
        ),
    )
    default_role: Literal["director", "accountant", "employee"] = Field(
        default="accountant",
        examples=["accountant"],
        description="Default role assigned to new users in this tenant",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the tenant is currently active",
    )

    @field_validator("schema_name")
    @classmethod
    def _schema_name_format(cls, v: str | None) -> str | None:
        if v is not None and not _SCHEMA_NAME_RE.match(v):
            msg = "schema_name must match pattern ^tenant_[a-z0-9_]+$ (e.g. 'tenant_firma')"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# TenantUpdate — all fields Optional
# ---------------------------------------------------------------------------


class TenantUpdate(BaseModel):
    """Schema for updating a tenant.

    All fields optional — only supplied fields are updated.
    schema_name is immutable and therefore excluded.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    ico: str | None = Field(default=None, max_length=8)
    dic: str | None = Field(default=None, max_length=12)
    ic_dph: str | None = Field(default=None, max_length=14)
    address_street: str | None = Field(default=None, min_length=1, max_length=200)
    address_city: str | None = Field(default=None, min_length=1, max_length=100)
    address_zip: str | None = Field(default=None, min_length=1, max_length=10)
    address_country: str | None = Field(default=None, max_length=2)
    bank_iban: str | None = Field(default=None, max_length=34)
    bank_bic: str | None = Field(default=None, max_length=11)
    default_role: Literal["director", "accountant", "employee"] | None = Field(
        default=None,
    )
    is_active: bool | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.strip():
                msg = "Name must not be blank"
                raise ValueError(msg)
            return v.strip()
        return v

    @field_validator("ico")
    @classmethod
    def _ico_must_be_8_digits(cls, v: str | None) -> str | None:
        if v is not None and not _ICO_RE.match(v):
            msg = "IČO must be exactly 8 digits"
            raise ValueError(msg)
        return v

    @field_validator("dic")
    @classmethod
    def _dic_format(cls, v: str | None) -> str | None:
        if v is not None and not _DIC_RE.match(v):
            msg = "DIČ must be 10-12 digits"
            raise ValueError(msg)
        return v

    @field_validator("ic_dph")
    @classmethod
    def _ic_dph_format(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.upper()
            if not _IC_DPH_RE.match(cleaned):
                msg = "IČ DPH must match format SK + 10 digits (e.g. SK2012345678)"
                raise ValueError(msg)
            return cleaned
        return v

    @field_validator("address_country")
    @classmethod
    def _country_code_format(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.upper()
            if not _COUNTRY_RE.match(cleaned):
                msg = "Country must be a 2-letter ISO 3166-1 alpha-2 code"
                raise ValueError(msg)
            return cleaned
        return v

    @field_validator("bank_iban")
    @classmethod
    def _validate_iban(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_iban(v)
        return v

    @field_validator("bank_bic")
    @classmethod
    def _validate_bic(cls, v: str | None) -> str | None:
        return _validate_bic(v)


# ---------------------------------------------------------------------------
# TenantInDB — full representation from database (all columns)
# ---------------------------------------------------------------------------


class TenantInDB(TenantBase):
    """Full tenant representation as stored in the database.

    Includes all model columns (PK, schema_name, flags, timestamps).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schema_name: str
    default_role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Backward-compatible alias — existing code imports TenantRead
TenantRead = TenantInDB


# ---------------------------------------------------------------------------
# TenantPublic — safe subset for API responses
# ---------------------------------------------------------------------------


class TenantPublic(BaseModel):
    """Safe subset of tenant data exposed in public-facing API responses.

    Omits sensitive fields like bank details and full address.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    ico: str
    schema_name: str
    is_active: bool
