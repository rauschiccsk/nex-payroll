"""Pydantic v2 schemas for Tenant entity.

Used for API request validation (Create/Update) and response serialisation (Read).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TenantCreate(BaseModel):
    """Schema for creating a new tenant (company)."""

    name: str = Field(
        ...,
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
        description="Company bank account IBAN",
    )
    bank_bic: str | None = Field(
        default=None,
        max_length=11,
        description="BIC/SWIFT code; null if domestic-only",
    )
    default_role: str = Field(
        default="accountant",
        max_length=20,
        examples=["accountant"],
        description="Default role assigned to new users in this tenant",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the tenant is currently active",
    )


class TenantUpdate(BaseModel):
    """Schema for updating a tenant.

    All fields optional — only supplied fields are updated.
    """

    name: str | None = Field(
        default=None,
        max_length=200,
    )
    ico: str | None = Field(
        default=None,
        max_length=8,
    )
    dic: str | None = Field(
        default=None,
        max_length=12,
    )
    ic_dph: str | None = Field(
        default=None,
        max_length=14,
    )
    address_street: str | None = Field(
        default=None,
        max_length=200,
    )
    address_city: str | None = Field(
        default=None,
        max_length=100,
    )
    address_zip: str | None = Field(
        default=None,
        max_length=10,
    )
    address_country: str | None = Field(
        default=None,
        max_length=2,
    )
    bank_iban: str | None = Field(
        default=None,
        max_length=34,
    )
    bank_bic: str | None = Field(
        default=None,
        max_length=11,
    )
    default_role: str | None = Field(
        default=None,
        max_length=20,
    )
    is_active: bool | None = Field(
        default=None,
    )


class TenantRead(BaseModel):
    """Schema for returning a tenant in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    ico: str
    dic: str | None
    ic_dph: str | None
    address_street: str
    address_city: str
    address_zip: str
    address_country: str
    bank_iban: str
    bank_bic: str | None
    schema_name: str
    default_role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
