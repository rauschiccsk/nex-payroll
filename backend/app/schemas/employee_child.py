"""Pydantic v2 schemas for EmployeeChild entity.

Used for API request validation (Create/Update) and response serialisation (Read).
PII field (birth_number) is represented as a plain string in the schema layer —
encryption/decryption is handled transparently by the ORM EncryptedString type.
"""

import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

# Slovak birth number (rodne cislo): 6 digits + optional slash + 3-4 digits
_BIRTH_NUMBER_RE = re.compile(r"^\d{6}/?(\d{3,4})$")


def _strip_not_blank(value: str, field_name: str) -> str:
    """Strip whitespace and ensure not blank."""
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} must not be blank"
        raise ValueError(msg)
    return stripped


# ---------------------------------------------------------------------------
# EmployeeChildCreate
# ---------------------------------------------------------------------------


class EmployeeChildCreate(BaseModel):
    """Schema for creating a new employee child record (daňový bonus)."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    employee_id: UUID = Field(
        ...,
        description="Reference to parent employee (employees.id)",
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Anna"],
        description="Child first name",
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["Nováková"],
        description="Child last name",
    )
    birth_date: date = Field(
        ...,
        examples=["2015-03-20"],
        description="Child date of birth",
    )
    birth_number: str | None = Field(
        default=None,
        max_length=20,
        examples=["1503200001"],
        description="Child birth number (rodné číslo) — stored encrypted",
    )
    is_tax_bonus_eligible: bool = Field(
        default=True,
        description="Whether the child is eligible for daňový bonus",
    )
    custody_from: date | None = Field(
        default=None,
        examples=["2015-03-20"],
        description="Start of custody period (NULL = since birth)",
    )
    custody_to: date | None = Field(
        default=None,
        description="End of custody period (NULL = ongoing)",
    )

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
    def _birth_number_format(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.replace("/", "")
            if not _BIRTH_NUMBER_RE.match(v) and not _BIRTH_NUMBER_RE.match(cleaned):
                msg = "Birth number must be in format YYMMDDNNN or YYMMDD/NNNN"
                raise ValueError(msg)
            return cleaned
        return v

    @field_validator("custody_to")
    @classmethod
    def _custody_to_after_from(cls, v: date | None, info: object) -> date | None:
        """Ensure custody_to is on or after custody_from when both are set."""
        if v is not None and hasattr(info, "data"):
            custody_from = info.data.get("custody_from")  # type: ignore[union-attr]
            if custody_from is not None and v < custody_from:
                msg = "custody_to must be on or after custody_from"
                raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# EmployeeChildUpdate
# ---------------------------------------------------------------------------


class EmployeeChildUpdate(BaseModel):
    """Schema for updating an employee child record.

    All fields optional — only supplied fields are updated.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    birth_date: date | None = Field(default=None)
    birth_number: str | None = Field(default=None, max_length=20)
    is_tax_bonus_eligible: bool | None = Field(default=None)
    custody_from: date | None = Field(default=None)
    custody_to: date | None = Field(default=None)

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

    @field_validator("custody_to")
    @classmethod
    def _custody_to_after_from(cls, v: date | None, info: object) -> date | None:
        """Ensure custody_to is on or after custody_from when both are set."""
        if v is not None and hasattr(info, "data"):
            custody_from = info.data.get("custody_from")  # type: ignore[union-attr]
            if custody_from is not None and v < custody_from:
                msg = "custody_to must be on or after custody_from"
                raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# EmployeeChildRead
# ---------------------------------------------------------------------------


class EmployeeChildRead(BaseModel):
    """Schema for returning an employee child record in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID
    first_name: str
    last_name: str
    birth_date: date
    birth_number: str | None
    is_tax_bonus_eligible: bool
    custody_from: date | None
    custody_to: date | None
    created_at: datetime
    updated_at: datetime
