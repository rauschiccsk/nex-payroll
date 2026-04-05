"""LeaveEntitlement model — annual leave entitlement per employee.

Schema: tenant-specific
Tracks total, used, remaining, and carryover leave days for each
employee per calendar year.
"""

import uuid

from sqlalchemy import (
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class LeaveEntitlement(UUIDMixin, TimestampMixin, Base):
    """Annual leave entitlement for an employee.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each employee has one entitlement record per calendar year,
    tracking total days, used days, remaining days, and carryover
    from the previous year.
    """

    __tablename__ = "leave_entitlements"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "employee_id",
            "year",
            name="uq_leave_entitlements_tenant_employee_year",
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

    # -- Entitlement details --

    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Calendar year of the entitlement",
    )

    total_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total annual leave days entitled",
    )

    used_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of leave days already used",
    )

    remaining_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Remaining leave days (computed: total - used)",
    )

    carryover_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Leave days carried over from previous year",
    )

    def __repr__(self) -> str:
        return (
            f"<LeaveEntitlement(employee_id={self.employee_id!r}, "
            f"year={self.year!r}, "
            f"remaining={self.remaining_days!r})>"
        )
