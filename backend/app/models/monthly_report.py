"""MonthlyReport model — monthly report (SP/ZP/DÚ) for a tenant.

Schema: tenant-specific
Represents generated statutory reports submitted to social insurance,
health insurers, or tax authorities on a monthly basis.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class MonthlyReport(UUIDMixin, TimestampMixin, Base):
    """Monthly statutory report belonging to a specific tenant.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each tenant generates monthly reports for social insurance (SP),
    health insurers (ZP), and tax authority (DÚ).
    One record per (tenant, year, month, report_type).
    """

    __tablename__ = "monthly_reports"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "period_year",
            "period_month",
            "report_type",
            name="uq_monthly_reports_tenant_year_month_type",
        ),
        CheckConstraint(
            "report_type IN ('sp_monthly', 'zp_vszp', 'zp_dovera', "
            "'zp_union', 'tax_prehled')",
            name="ck_monthly_reports_report_type",
        ),
        CheckConstraint(
            "status IN ('generated', 'submitted', 'accepted', 'rejected')",
            name="ck_monthly_reports_status",
        ),
        Index(
            "ix_monthly_reports_tenant_period",
            "tenant_id",
            "period_year",
            "period_month",
        ),
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        comment="Reference to owning tenant",
    )

    health_insurer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared.health_insurers.id"),
        nullable=True,
        comment="Reference to health insurer (for ZP report types)",
    )

    # -- Period --

    period_year: Mapped[int] = mapped_column(
        nullable=False,
        comment="Report period — calendar year",
    )

    period_month: Mapped[int] = mapped_column(
        nullable=False,
        comment="Report period — calendar month (1-12)",
    )

    # -- Report details --

    report_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Report type: sp_monthly, zp_vszp, zp_dovera, zp_union, tax_prehled",
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Path to generated report file",
    )

    file_format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="xml",
        comment="File format of the report (default: xml)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="generated",
        comment="Report status: generated, submitted, accepted, rejected",
    )

    deadline_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Statutory deadline date for submission",
    )

    institution: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Target institution (e.g. Sociálna poisťovňa, VšZP)",
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when the report was submitted",
    )

    def __repr__(self) -> str:
        return (
            f"<MonthlyReport(type={self.report_type!r}, "
            f"period={self.period_year!r}/{self.period_month!r}, "
            f"status={self.status!r})>"
        )
