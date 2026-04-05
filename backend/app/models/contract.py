"""Contract model — employment contract record.

Schema: tenant-specific
Represents a work contract between tenant (employer) and employee.
Supports permanent, fixed-term, and agreement-based contract types.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Contract(UUIDMixin, TimestampMixin, Base):
    """Employment contract belonging to a specific tenant.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each employee may have multiple contracts; only one should be current
    at a time (is_current=True).
    """

    __tablename__ = "contracts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "contract_number",
            name="uq_contracts_tenant_contract_number",
        ),
        CheckConstraint(
            "contract_type IN ('permanent', 'fixed_term', 'agreement_work', 'agreement_activity')",
            name="ck_contracts_contract_type",
        ),
        CheckConstraint(
            "wage_type IN ('monthly', 'hourly')",
            name="ck_contracts_wage_type",
        ),
        Index(
            "ix_contracts_tenant_employee_current",
            "tenant_id",
            "employee_id",
            "is_current",
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

    # -- Contract identification --

    contract_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unique contract number within tenant",
    )

    contract_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Contract type: permanent, fixed_term, agreement_work, agreement_activity",
    )

    # -- Job details --

    job_title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Job position title",
    )

    wage_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Wage type: monthly or hourly",
    )

    base_wage: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Base wage amount (monthly or hourly rate)",
    )

    hours_per_week: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        nullable=False,
        server_default="40.0",
        comment="Contracted weekly working hours",
    )

    # -- Dates --

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Contract start date",
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Contract end date (NULL for indefinite contracts)",
    )

    probation_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="End date of probation period",
    )

    termination_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Actual termination date (NULL if not terminated)",
    )

    termination_reason: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Reason for contract termination",
    )

    # -- Status --

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether this is the currently active contract",
    )

    def __repr__(self) -> str:
        return (
            f"<Contract(contract_number={self.contract_number!r}, "
            f"type={self.contract_type!r}, "
            f"is_current={self.is_current!r})>"
        )
