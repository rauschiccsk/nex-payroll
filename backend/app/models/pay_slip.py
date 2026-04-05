"""PaySlip model — generated pay slip PDF for an employee.

Schema: tenant-specific
Stores metadata about generated pay slip PDFs linked to approved payrolls.
Tracks PDF file path, size, generation time, and employee download status.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin, UUIDMixin


class PaySlip(UUIDMixin, TimestampMixin, Base):
    """Pay slip PDF record for a single payroll period.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each record links to an approved payroll and stores the path to
    the generated PDF file. The downloaded_at field tracks when the
    employee first accessed the document (audit trail).

    Note: TimestampMixin provides created_at and updated_at.
    The DESIGN.md spec shows generated_at instead of created_at,
    so we add an explicit generated_at column alongside the mixin fields.
    """

    __tablename__ = "pay_slips"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "payroll_id",
            name="uq_pay_slips_tenant_payroll",
        ),
        Index(
            "ix_pay_slips_tenant_employee_period",
            "tenant_id",
            "employee_id",
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

    payroll_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payrolls.id"),
        nullable=False,
        comment="Reference to the approved payroll record",
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
        nullable=False,
        comment="Reference to the employee",
    )

    # -- Period --

    period_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Pay slip period year (e.g. 2025)",
    )

    period_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Pay slip period month (1-12)",
    )

    # -- PDF file metadata --

    pdf_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Absolute path to generated PDF file",
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="PDF file size in bytes",
    )

    # -- Timestamps --

    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the pay slip PDF was generated",
    )

    downloaded_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when employee first downloaded the pay slip",
    )

    def __repr__(self) -> str:
        return (
            f"<PaySlip(employee_id={self.employee_id!r}, "
            f"period={self.period_year}/{self.period_month}, "
            f"pdf_path={self.pdf_path!r})>"
        )
