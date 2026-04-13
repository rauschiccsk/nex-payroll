"""Pydantic v2 schemas for PaymentOrder entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each payment order represents a single bank transfer instruction generated from
approved payroll — covering net wages, social/health insurance, tax, or pillar-2.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_PAYMENT_TYPE = Literal["net_wage", "sp", "zp_vszp", "zp_dovera", "zp_union", "tax", "pillar2"]
_PAYMENT_STATUS = Literal["pending", "exported", "paid"]

_ZP_PAYMENT_TYPES = {"zp_vszp", "zp_dovera", "zp_union"}

_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_not_blank(value: str, field_name: str) -> str:
    """Strip whitespace and ensure not blank."""
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} must not be blank"
        raise ValueError(msg)
    return stripped


# ---------------------------------------------------------------------------
# PaymentOrderCreate
# ---------------------------------------------------------------------------


class PaymentOrderCreate(BaseModel):
    """Schema for creating a new payment order."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    period_year: int = Field(
        ...,
        ge=2000,
        le=2100,
        examples=[2025],
        description="Payroll period — calendar year",
    )
    period_month: int = Field(
        ...,
        ge=1,
        le=12,
        examples=[1],
        description="Payroll period — calendar month (1-12)",
    )
    payment_type: _PAYMENT_TYPE = Field(
        ...,
        examples=["net_wage"],
        description=("Payment type: net_wage, sp, zp_vszp, zp_dovera, zp_union, tax, pillar2"),
    )
    recipient_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Ján Novák"],
        description="Recipient (beneficiary) name",
    )
    recipient_iban: str = Field(
        ...,
        min_length=5,
        max_length=34,
        examples=["SK3112000000198742637541"],
        description="Recipient IBAN",
    )
    recipient_bic: str | None = Field(
        default=None,
        max_length=11,
        examples=["TATRSKBX"],
        description="Recipient BIC/SWIFT code",
    )
    amount: Decimal = Field(
        ...,
        max_digits=12,
        decimal_places=2,
        gt=0,
        examples=["1234.56"],
        description="Payment amount in EUR (must be positive)",
    )
    variable_symbol: str | None = Field(
        default=None,
        max_length=10,
        examples=["1234567890"],
        description="Variable symbol for bank transfer",
    )
    specific_symbol: str | None = Field(
        default=None,
        max_length=10,
        examples=["0012345678"],
        description="Specific symbol for bank transfer",
    )
    constant_symbol: str | None = Field(
        default=None,
        max_length=4,
        examples=["0558"],
        description="Constant symbol for bank transfer",
    )
    reference: str | None = Field(
        default=None,
        max_length=140,
        examples=["PAYROLL-2025-01-NOVAK"],
        description="SEPA end-to-end reference",
    )
    status: _PAYMENT_STATUS = Field(
        default="pending",
        examples=["pending"],
        description="Order status: pending, exported, paid",
    )
    employee_id: UUID | None = Field(
        default=None,
        description="Reference to employee (for net_wage type)",
    )
    health_insurer_id: UUID | None = Field(
        default=None,
        description="Reference to health insurer (for ZP payment types)",
    )

    # -- Field validators ----------------------------------------------------

    @field_validator("recipient_name")
    @classmethod
    def _recipient_name_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "recipient_name")

    @field_validator("recipient_iban")
    @classmethod
    def _validate_iban(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").upper()
        if not cleaned:
            msg = "recipient_iban must not be blank"
            raise ValueError(msg)
        if not _IBAN_RE.match(cleaned):
            msg = "recipient_iban must be a valid IBAN format"
            raise ValueError(msg)
        return cleaned

    @field_validator("recipient_bic")
    @classmethod
    def _strip_bic(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip().upper()
            return stripped or None
        return v

    # -- Model validators ----------------------------------------------------

    @model_validator(mode="after")
    def _check_payment_type_refs(self) -> "PaymentOrderCreate":
        """Validate that net_wage has employee_id and ZP types have health_insurer_id."""
        if self.payment_type == "net_wage" and self.employee_id is None:
            msg = "employee_id is required for payment_type 'net_wage'"
            raise ValueError(msg)
        if self.payment_type in _ZP_PAYMENT_TYPES and self.health_insurer_id is None:
            msg = f"health_insurer_id is required for payment_type '{self.payment_type}'"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# PaymentOrderUpdate
# ---------------------------------------------------------------------------


class PaymentOrderUpdate(BaseModel):
    """Schema for updating a payment order.

    All fields optional — only supplied fields are updated.
    """

    recipient_name: str | None = Field(default=None, min_length=1, max_length=200)
    recipient_iban: str | None = Field(default=None, min_length=5, max_length=34)
    recipient_bic: str | None = Field(default=None, max_length=11)
    amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2, gt=0)
    variable_symbol: str | None = Field(default=None, max_length=10)
    specific_symbol: str | None = Field(default=None, max_length=10)
    constant_symbol: str | None = Field(default=None, max_length=4)
    reference: str | None = Field(default=None, max_length=140)
    status: _PAYMENT_STATUS | None = Field(default=None)
    employee_id: UUID | None = Field(default=None)
    health_insurer_id: UUID | None = Field(default=None)

    @field_validator("recipient_name")
    @classmethod
    def _recipient_name_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "recipient_name")
        return v

    @field_validator("recipient_iban")
    @classmethod
    def _validate_iban(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip().replace(" ", "").upper()
            if not cleaned:
                msg = "recipient_iban must not be blank"
                raise ValueError(msg)
            if not _IBAN_RE.match(cleaned):
                msg = "recipient_iban must be a valid IBAN format"
                raise ValueError(msg)
            return cleaned
        return v

    @field_validator("recipient_bic")
    @classmethod
    def _strip_bic(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip().upper()
            return stripped or None
        return v


# ---------------------------------------------------------------------------
# PaymentOrderRead
# ---------------------------------------------------------------------------


class PaymentOrderRead(BaseModel):
    """Schema for returning a payment order in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    period_year: int
    period_month: int
    payment_type: str
    recipient_name: str
    recipient_iban: str
    recipient_bic: str | None
    amount: Decimal
    variable_symbol: str | None
    specific_symbol: str | None
    constant_symbol: str | None
    reference: str | None
    status: str
    employee_id: UUID | None
    health_insurer_id: UUID | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# PaymentOrderStatusUpdate — for PUT /payments/{id}/status
# ---------------------------------------------------------------------------


class PaymentOrderStatusUpdate(BaseModel):
    """Schema for updating only the status of a payment order."""

    status: _PAYMENT_STATUS = Field(
        ...,
        examples=["exported"],
        description="New status: pending, exported, paid",
    )


# ---------------------------------------------------------------------------
# SepaXmlRequest — for POST /payments/{year}/{month}/sepa-xml
# ---------------------------------------------------------------------------


class SepaXmlRequest(BaseModel):
    """Optional parameters for SEPA XML generation."""

    tenant_id: UUID = Field(
        ...,
        description="Tenant whose payment orders to export",
    )
    execution_date: datetime | None = Field(
        default=None,
        description="Requested execution date (defaults to today)",
    )
