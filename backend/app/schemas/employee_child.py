"""Pydantic v2 schemas for EmployeeChild entity.

Used for API request validation (Create/Update) and response serialisation (Read).
PII field (birth_number) is represented as a plain string in the schema layer —
encryption/decryption is handled transparently by the ORM EncryptedString type.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
        max_length=100,
        examples=["Anna"],
        description="Child first name",
    )
    last_name: str = Field(
        ...,
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


# ---------------------------------------------------------------------------
# EmployeeChildUpdate
# ---------------------------------------------------------------------------


class EmployeeChildUpdate(BaseModel):
    """Schema for updating an employee child record.

    All fields optional — only supplied fields are updated.
    """

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = Field(default=None)
    birth_number: str | None = Field(default=None, max_length=20)
    is_tax_bonus_eligible: bool | None = Field(default=None)
    custody_from: date | None = Field(default=None)
    custody_to: date | None = Field(default=None)


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
