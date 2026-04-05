"""Pydantic v2 schemas for PaymentOrder entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each payment order represents a single bank transfer instruction generated from
approved payroll — covering net wages, social/health insurance, tax, or pillar-2.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_PAYMENT_TYPE = Literal["net_wage", "sp", "zp_vszp", "zp_dovera", "zp_union", "tax", "pillar2"]
_PAYMENT_STATUS = Literal["pending", "exported", "paid"]


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
        description="Payment type: net_wage, sp, zp_vszp, zp_dovera, zp_union, tax, pillar2",
    )
    recipient_name: str = Field(
        ...,
        max_length=200,
        examples=["Ján Novák"],
        description="Recipient (beneficiary) name",
    )
    recipient_iban: str = Field(
        ...,
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


# ---------------------------------------------------------------------------
# PaymentOrderUpdate
# ---------------------------------------------------------------------------


class PaymentOrderUpdate(BaseModel):
    """Schema for updating a payment order.

    All fields optional — only supplied fields are updated.
    """

    recipient_name: str | None = Field(default=None, max_length=200)
    recipient_iban: str | None = Field(default=None, max_length=34)
    recipient_bic: str | None = Field(default=None, max_length=11)
    amount: Decimal | None = Field(default=None, max_digits=12, decimal_places=2, gt=0)
    variable_symbol: str | None = Field(default=None, max_length=10)
    specific_symbol: str | None = Field(default=None, max_length=10)
    constant_symbol: str | None = Field(default=None, max_length=4)
    reference: str | None = Field(default=None, max_length=140)
    status: _PAYMENT_STATUS | None = Field(default=None)
    employee_id: UUID | None = Field(default=None)
    health_insurer_id: UUID | None = Field(default=None)


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
