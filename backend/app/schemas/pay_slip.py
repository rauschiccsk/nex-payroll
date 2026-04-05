"""Pydantic v2 schemas for PaySlip entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each record represents metadata about a generated pay slip PDF linked to an
approved payroll, including file path, size, and download tracking.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# PaySlipCreate
# ---------------------------------------------------------------------------


class PaySlipCreate(BaseModel):
    """Schema for creating a new pay slip record."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    payroll_id: UUID = Field(
        ...,
        description="Reference to the approved payroll record (payrolls.id)",
    )
    employee_id: UUID = Field(
        ...,
        description="Reference to the employee (employees.id)",
    )
    period_year: int = Field(
        ...,
        ge=2000,
        le=2100,
        examples=[2025],
        description="Pay slip period year (e.g. 2025)",
    )
    period_month: int = Field(
        ...,
        ge=1,
        le=12,
        examples=[1],
        description="Pay slip period month (1-12)",
    )
    pdf_path: str = Field(
        ...,
        max_length=500,
        examples=["/opt/nex-payroll-src/data/payslips/tenant1/2025/01/EMP001.pdf"],
        description="Absolute path to the generated PDF file",
    )
    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
        examples=[52480],
        description="PDF file size in bytes",
    )


# ---------------------------------------------------------------------------
# PaySlipUpdate
# ---------------------------------------------------------------------------


class PaySlipUpdate(BaseModel):
    """Schema for updating a pay slip record.

    All fields optional — only supplied fields are updated.
    """

    payroll_id: UUID | None = Field(
        default=None,
        description="Reference to the approved payroll record (payrolls.id)",
    )
    employee_id: UUID | None = Field(
        default=None,
        description="Reference to the employee (employees.id)",
    )
    period_year: int | None = Field(
        default=None,
        ge=2000,
        le=2100,
        description="Pay slip period year (e.g. 2025)",
    )
    period_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Pay slip period month (1-12)",
    )
    pdf_path: str | None = Field(
        default=None,
        max_length=500,
        description="Absolute path to the generated PDF file",
    )
    file_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="PDF file size in bytes",
    )
    downloaded_at: datetime | None = Field(
        default=None,
        description="Timestamp when employee first downloaded the pay slip",
    )


# ---------------------------------------------------------------------------
# PaySlipRead
# ---------------------------------------------------------------------------


class PaySlipRead(BaseModel):
    """Schema for returning a pay slip record in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    payroll_id: UUID
    employee_id: UUID
    period_year: int
    period_month: int
    pdf_path: str
    file_size_bytes: int | None
    generated_at: datetime
    downloaded_at: datetime | None
    created_at: datetime
    updated_at: datetime
