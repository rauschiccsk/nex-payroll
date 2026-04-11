"""Pydantic v2 schemas for MonthlyReport entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each tenant generates monthly statutory reports for social insurance (SP),
health insurers (ZP), and tax authority (DÚ).
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_REPORT_TYPE = Literal["sp_monthly", "zp_vszp", "zp_dovera", "zp_union", "tax_prehled"]
_REPORT_STATUS = Literal["generated", "submitted", "accepted", "rejected"]
_FILE_FORMAT = Literal["xml", "pdf"]

_ZP_REPORT_TYPES = {"zp_vszp", "zp_dovera", "zp_union"}


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
        min_length=1,
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
        min_length=1,
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

    @field_validator("file_path")
    @classmethod
    def _file_path_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "file_path")

    @field_validator("institution")
    @classmethod
    def _institution_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "institution")

    @model_validator(mode="after")
    def _check_health_insurer_for_zp(self) -> "MonthlyReportCreate":
        """ZP report types must have health_insurer_id set."""
        if self.report_type in _ZP_REPORT_TYPES and self.health_insurer_id is None:
            msg = f"health_insurer_id is required for report_type '{self.report_type}'"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# MonthlyReportUpdate
# ---------------------------------------------------------------------------


class MonthlyReportUpdate(BaseModel):
    """Schema for updating a monthly report.

    All fields optional — only supplied fields are updated.
    """

    file_path: str | None = Field(default=None, min_length=1, max_length=500)
    file_format: _FILE_FORMAT | None = Field(default=None)
    status: _REPORT_STATUS | None = Field(default=None)
    deadline_date: date | None = Field(default=None)
    institution: str | None = Field(default=None, min_length=1, max_length=100)
    submitted_at: datetime | None = Field(default=None)
    health_insurer_id: UUID | None = Field(default=None)

    @field_validator("file_path")
    @classmethod
    def _file_path_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "file_path")
        return v

    @field_validator("institution")
    @classmethod
    def _institution_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "institution")
        return v


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
