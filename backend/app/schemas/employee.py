"""Pydantic v2 schemas for Employee entity.

Used for API request validation (Create/Update) and response serialisation (Read).
PII fields (birth_number, bank_iban) are represented as plain strings in the schema
layer — encryption/decryption is handled transparently by the ORM EncryptedString type.
"""

import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_GENDER = Literal["M", "F"]
_TAX_DECLARATION = Literal["standard", "secondary", "none"]
_STATUS = Literal["active", "inactive", "terminated"]

# ---------------------------------------------------------------------------
# Validation patterns
# ---------------------------------------------------------------------------

# IBAN: 2-letter country code + 2 check digits + up to 30 alphanumeric
_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$")
# BIC/SWIFT: 8 or 11 alphanumeric characters
_BIC_RE = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")
# ISO 3166-1 alpha-2 country code
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
# Slovak birth number (rodne cislo): 6 digits + optional slash + 3-4 digits
_BIRTH_NUMBER_RE = re.compile(r"^\d{6}/?(\d{3,4})$")


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


def _validate_country(value: str) -> str:
    """Validate ISO 3166-1 alpha-2 country code."""
    cleaned = value.upper()
    if not _COUNTRY_RE.match(cleaned):
        msg = "Country must be a 2-letter ISO 3166-1 alpha-2 code"
        raise ValueError(msg)
    return cleaned


def _strip_not_blank(value: str, field_name: str) -> str:
    """Strip whitespace and ensure not blank."""
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} must not be blank"
        raise ValueError(msg)
    return stripped


# ---------------------------------------------------------------------------
# EmployeeCreate
# ---------------------------------------------------------------------------


class EmployeeCreate(BaseModel):
    """Schema for creating a new employee."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    employee_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
        examples=["EMP001"],
        description="Unique employee number within tenant",
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Ján"],
        description="First name",
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Novák"],
        description="Last name",
    )
    title_before: str | None = Field(
        default=None,
        max_length=50,
        examples=["Ing."],
        description="Academic title before name (e.g. Ing., Mgr.)",
    )
    title_after: str | None = Field(
        default=None,
        max_length=50,
        examples=["PhD."],
        description="Academic title after name (e.g. PhD., CSc.)",
    )
    birth_date: date = Field(
        ...,
        examples=["1990-05-15"],
        description="Date of birth",
    )
    birth_number: str = Field(
        ...,
        max_length=20,
        examples=["9005150001"],
        description="Slovak birth number (rodné číslo) — stored encrypted",
    )
    gender: _GENDER = Field(
        ...,
        examples=["M"],
        description="Gender: M (male) or F (female)",
    )
    nationality: str = Field(
        default="SK",
        max_length=2,
        examples=["SK"],
        description="ISO 3166-1 alpha-2 nationality code",
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
        description="Employee bank account IBAN — stored encrypted",
    )
    bank_bic: str | None = Field(
        default=None,
        max_length=11,
        examples=["SUBASKBX"],
        description="BIC/SWIFT code; null if domestic-only",
    )
    health_insurer_id: UUID = Field(
        ...,
        description="Reference to health insurance company (shared.health_insurers.id)",
    )
    tax_declaration_type: _TAX_DECLARATION = Field(
        ...,
        examples=["standard"],
        description="Tax declaration type: standard, secondary, none",
    )
    nczd_applied: bool = Field(
        default=True,
        description="Whether NČZD (non-taxable amount) is applied",
    )
    pillar2_saver: bool = Field(
        default=False,
        description="Whether employee is a 2nd pillar saver",
    )
    is_disabled: bool = Field(
        default=False,
        description="Whether employee has a disability status",
    )
    status: _STATUS = Field(
        default="active",
        examples=["active"],
        description="Employment status: active, inactive, terminated",
    )
    hire_date: date = Field(
        ...,
        examples=["2024-01-15"],
        description="Date of hire",
    )
    termination_date: date | None = Field(
        default=None,
        examples=["2025-12-31"],
        description="Date of employment termination (null if still employed)",
    )

    @field_validator("employee_number")
    @classmethod
    def _employee_number_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "Employee number")

    @field_validator("first_name")
    @classmethod
    def _first_name_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "First name")

    @field_validator("last_name")
    @classmethod
    def _last_name_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "Last name")

    @field_validator("birth_number")
    @classmethod
    def _birth_number_format(cls, v: str) -> str:
        cleaned = v.replace("/", "")
        if not _BIRTH_NUMBER_RE.match(v) and not _BIRTH_NUMBER_RE.match(cleaned):
            msg = "Birth number must be in format YYMMDDNNN or YYMMDD/NNNN"
            raise ValueError(msg)
        return cleaned

    @field_validator("nationality")
    @classmethod
    def _nationality_format(cls, v: str) -> str:
        return _validate_country(v)

    @field_validator("address_country")
    @classmethod
    def _address_country_format(cls, v: str) -> str:
        return _validate_country(v)

    @field_validator("bank_iban")
    @classmethod
    def _validate_iban(cls, v: str) -> str:
        return _validate_iban(v)

    @field_validator("bank_bic")
    @classmethod
    def _validate_bic(cls, v: str | None) -> str | None:
        return _validate_bic(v)

    @field_validator("termination_date")
    @classmethod
    def _termination_after_hire(cls, v: date | None, info: object) -> date | None:
        """Ensure termination_date is after hire_date when both are set."""
        if v is not None and hasattr(info, "data"):
            hire = info.data.get("hire_date")  # type: ignore[union-attr]
            if hire is not None and v < hire:
                msg = "Termination date must be on or after hire date"
                raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# EmployeeUpdate
# ---------------------------------------------------------------------------


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee.

    All fields optional — only supplied fields are updated.
    """

    employee_number: str | None = Field(default=None, min_length=1, max_length=20)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    title_before: str | None = Field(default=None, max_length=50)
    title_after: str | None = Field(default=None, max_length=50)
    birth_date: date | None = Field(default=None)
    birth_number: str | None = Field(default=None, max_length=20)
    gender: _GENDER | None = Field(default=None)
    nationality: str | None = Field(default=None, max_length=2)
    address_street: str | None = Field(default=None, min_length=1, max_length=200)
    address_city: str | None = Field(default=None, min_length=1, max_length=100)
    address_zip: str | None = Field(default=None, min_length=1, max_length=10)
    address_country: str | None = Field(default=None, max_length=2)
    bank_iban: str | None = Field(default=None, max_length=34)
    bank_bic: str | None = Field(default=None, max_length=11)
    health_insurer_id: UUID | None = Field(default=None)
    tax_declaration_type: _TAX_DECLARATION | None = Field(default=None)
    nczd_applied: bool | None = Field(default=None)
    pillar2_saver: bool | None = Field(default=None)
    is_disabled: bool | None = Field(default=None)
    status: _STATUS | None = Field(default=None)
    hire_date: date | None = Field(default=None)
    termination_date: date | None = Field(default=None)

    @field_validator("employee_number")
    @classmethod
    def _employee_number_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "Employee number")
        return v

    @field_validator("first_name")
    @classmethod
    def _first_name_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "First name")
        return v

    @field_validator("last_name")
    @classmethod
    def _last_name_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "Last name")
        return v

    @field_validator("birth_number")
    @classmethod
    def _birth_number_format(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.replace("/", "")
            if not _BIRTH_NUMBER_RE.match(v) and not _BIRTH_NUMBER_RE.match(cleaned):
                msg = "Birth number must be in format YYMMDDNNN or YYMMDD/NNNN"
                raise ValueError(msg)
            return cleaned
        return v

    @field_validator("nationality")
    @classmethod
    def _nationality_format(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_country(v)
        return v

    @field_validator("address_country")
    @classmethod
    def _address_country_format(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_country(v)
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
# EmployeeRead
# ---------------------------------------------------------------------------


class EmployeeRead(BaseModel):
    """Schema for returning an employee in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_number: str
    first_name: str
    last_name: str
    title_before: str | None
    title_after: str | None
    birth_date: date
    birth_number: str
    gender: str
    nationality: str
    address_street: str
    address_city: str
    address_zip: str
    address_country: str
    bank_iban: str
    bank_bic: str | None
    health_insurer_id: UUID
    tax_declaration_type: str
    nczd_applied: bool
    pillar2_saver: bool
    is_disabled: bool
    status: str
    hire_date: date
    termination_date: date | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
