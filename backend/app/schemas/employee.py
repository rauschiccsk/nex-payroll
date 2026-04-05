"""Pydantic v2 schemas for Employee entity.

Used for API request validation (Create/Update) and response serialisation (Read).
PII fields (birth_number, bank_iban) are represented as plain strings in the schema
layer — encryption/decryption is handled transparently by the ORM EncryptedString type.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_GENDER = Literal["M", "F"]
_TAX_DECLARATION = Literal["standard", "secondary", "none"]
_STATUS = Literal["active", "inactive", "terminated"]


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
        max_length=20,
        examples=["EMP001"],
        description="Unique employee number within tenant",
    )
    first_name: str = Field(
        ...,
        max_length=100,
        examples=["Ján"],
        description="First name",
    )
    last_name: str = Field(
        ...,
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
        max_length=200,
        examples=["Hlavná 1"],
        description="Street address",
    )
    address_city: str = Field(
        ...,
        max_length=100,
        examples=["Bratislava"],
        description="City",
    )
    address_zip: str = Field(
        ...,
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
    is_deleted: bool = Field(
        default=False,
        description="Soft-delete flag",
    )


# ---------------------------------------------------------------------------
# EmployeeUpdate
# ---------------------------------------------------------------------------


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee.

    All fields optional — only supplied fields are updated.
    """

    tenant_id: UUID | None = Field(default=None)
    employee_number: str | None = Field(default=None, max_length=20)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    title_before: str | None = Field(default=None, max_length=50)
    title_after: str | None = Field(default=None, max_length=50)
    birth_date: date | None = Field(default=None)
    birth_number: str | None = Field(default=None, max_length=20)
    gender: _GENDER | None = Field(default=None)
    nationality: str | None = Field(default=None, max_length=2)
    address_street: str | None = Field(default=None, max_length=200)
    address_city: str | None = Field(default=None, max_length=100)
    address_zip: str | None = Field(default=None, max_length=10)
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
    is_deleted: bool | None = Field(default=None)


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
