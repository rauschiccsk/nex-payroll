"""Leave model — leave / absence record for an employee.

Schema: tenant-specific
Tracks absences such as annual leave, sick leave (employer / SP),
OCR, maternity, parental, unpaid leave, and work obstacles.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Leave(UUIDMixin, TimestampMixin, Base):
    """Employee leave / absence record.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each record represents a single leave period for one employee,
    with a specific type, date range, and approval status.
    """

    __tablename__ = "leaves"
    __table_args__ = (
        CheckConstraint(
            "leave_type IN ('annual', 'sick_employer', 'sick_sp', "
            "'ocr', 'maternity', 'parental', 'unpaid', 'obstacle')",
            name="ck_leaves_leave_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="ck_leaves_status",
        ),
        Index(
            "ix_leaves_tenant_employee_start",
            "tenant_id",
            "employee_id",
            "start_date",
        ),
        Index(
            "ix_leaves_tenant_status",
            "tenant_id",
            "status",
        ),
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        comment="Reference to owning tenant",
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id"),
        nullable=False,
        comment="Reference to employee",
    )

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="User who approved/rejected the leave request",
    )

    # -- Leave details --

    leave_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment=("Leave type: annual, sick_employer, sick_sp, ocr, maternity, parental, unpaid, obstacle"),
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="First day of leave",
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Last day of leave",
    )

    business_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of business (working) days in the leave period",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
        comment="Leave status: pending, approved, rejected, cancelled",
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional note or reason for the leave request",
    )

    # -- Approval tracking --

    approved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when the leave was approved/rejected",
    )

    def __repr__(self) -> str:
        return (
            f"<Leave(employee_id={self.employee_id!r}, "
            f"type={self.leave_type!r}, "
            f"dates={self.start_date!r}–{self.end_date!r}, "
            f"status={self.status!r})>"
        )
