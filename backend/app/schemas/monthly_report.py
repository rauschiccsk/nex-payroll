"""Pydantic v2 schemas for MonthlyReport entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each tenant generates monthly statutory reports for social insurance (SP),
health insurers (ZP), and tax authority (DÚ).
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_REPORT_TYPE = Literal["sp_monthly", "zp_vszp", "zp_dovera", "zp_union", "tax_prehled"]
_REPORT_STATUS = Literal["generated", "submitted", "accepted", "rejected"]
_FILE_FORMAT = Literal["xml", "pdf"]


# ---------------------------------------------------------------------------
# MonthlyReportCreate
# ---------------------------------------------------------------------------


class MonthlyReportCreate(BaseModel):
    """Schema for creating a new monthly statutory report."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    period_year: int = Field(
        ...,
        ge=2000,
        le=2100,
        examples=[2025],
        description="Report period — calendar year",
    )
    period_month: int = Field(
        ...,
        ge=1,
        le=12,
        examples=[1],
        description="Report period — calendar month (1-12)",
    )
    report_type: _REPORT_TYPE = Field(
        ...,
        examples=["sp_monthly"],
        description="Report type: sp_monthly, zp_vszp, zp_dovera, zp_union, tax_prehled",
    )
    file_path: str = Field(
        ...,
        max_length=500,
        examples=["/opt/nex-payroll-src/data/reports/2025/01/sp_monthly.xml"],
        description="Path to generated report file",
    )
    file_format: _FILE_FORMAT = Field(
        default="xml",
        examples=["xml"],
        description="File format of the report (default: xml)",
    )
    status: _REPORT_STATUS = Field(
        default="generated",
        examples=["generated"],
        description="Report status: generated, submitted, accepted, rejected",
    )
    deadline_date: date = Field(
        ...,
        examples=["2025-02-20"],
        description="Statutory deadline date for submission",
    )
    institution: str = Field(
        ...,
        max_length=100,
        examples=["Sociálna poisťovňa"],
        description="Target institution (e.g. Sociálna poisťovňa, VšZP)",
    )
    submitted_at: datetime | None = Field(
        default=None,
        description="Timestamp when the report was submitted",
    )
    health_insurer_id: UUID | None = Field(
        default=None,
        description="Reference to health insurer (for ZP report types)",
    )


# ---------------------------------------------------------------------------
# MonthlyReportUpdate
# ---------------------------------------------------------------------------


class MonthlyReportUpdate(BaseModel):
    """Schema for updating a monthly report.

    All fields optional — only supplied fields are updated.
    """

    file_path: str | None = Field(default=None, max_length=500)
    file_format: _FILE_FORMAT | None = Field(default=None)
    status: _REPORT_STATUS | None = Field(default=None)
    deadline_date: date | None = Field(default=None)
    institution: str | None = Field(default=None, max_length=100)
    submitted_at: datetime | None = Field(default=None)
    health_insurer_id: UUID | None = Field(default=None)


# ---------------------------------------------------------------------------
# MonthlyReportRead
# ---------------------------------------------------------------------------


class MonthlyReportRead(BaseModel):
    """Schema for returning a monthly report in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    period_year: int
    period_month: int
    report_type: str
    file_path: str
    file_format: str
    status: str
    deadline_date: date
    institution: str
    submitted_at: datetime | None
    health_insurer_id: UUID | None
    created_at: datetime
    updated_at: datetime
