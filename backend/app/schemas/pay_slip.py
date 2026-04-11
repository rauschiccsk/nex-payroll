"""Pydantic v2 schemas for PaySlip entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each record represents metadata about a generated pay slip PDF linked to an
approved payroll, including file path, size, and download tracking.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
        min_length=1,
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

    @field_validator("pdf_path")
    @classmethod
    def _pdf_path_must_end_with_pdf(cls, v: str) -> str:
        """Ensure pdf_path ends with .pdf extension."""
        if not v.lower().endswith(".pdf"):
            msg = "pdf_path must end with '.pdf'"
            raise ValueError(msg)
        return v


# ---------------------------------------------------------------------------
# PaySlipUpdate
# ---------------------------------------------------------------------------


class PaySlipUpdate(BaseModel):
    """Schema for updating a pay slip record.

    All fields optional — only supplied fields are updated.
    Immutable FK/identity fields (payroll_id, employee_id, period_year,
    period_month) are excluded — a pay slip is generated from an approved
    payroll and those references must not change after creation.
    """

    pdf_path: str | None = Field(
        default=None,
        min_length=1,
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

    @field_validator("pdf_path")
    @classmethod
    def _pdf_path_must_end_with_pdf(cls, v: str | None) -> str | None:
        """Ensure pdf_path ends with .pdf extension when provided."""
        if v is not None and not v.lower().endswith(".pdf"):
            msg = "pdf_path must end with '.pdf'"
            raise ValueError(msg)
        return v


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
