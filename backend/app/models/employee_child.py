"""EmployeeChild model — child of an employee (for tax bonus calculation).

Schema: tenant-specific
Stores children data for daňový bonus (child tax credit) eligibility.
PII field (birth_number) is encrypted at rest using Fernet (AES-256).
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.types import EncryptedString


class EmployeeChild(UUIDMixin, TimestampMixin, Base):
    """Child of an employee — used for daňový bonus (child tax credit).

    Tenant-specific table — lives in the tenant's dedicated schema.
    PII field (birth_number) is encrypted with Fernet (AES-256).
    """

    __tablename__ = "employee_children"
    __table_args__ = (
        Index(
            "ix_employee_children_tenant_employee",
            "tenant_id",
            "employee_id",
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
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to parent employee",
    )

    # -- Child identification --

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Child first name",
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Child last name",
    )

    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Child date of birth",
    )

    birth_number: Mapped[str | None] = mapped_column(
        EncryptedString(),
        nullable=True,
        comment="Child birth number (rodné číslo) — encrypted at rest",
    )

    # -- Tax bonus eligibility --

    is_tax_bonus_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether the child is eligible for daňový bonus",
    )

    # -- Custody period --

    custody_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Start of custody period (NULL = since birth)",
    )

    custody_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="End of custody period (NULL = ongoing)",
    )

    def __repr__(self) -> str:
        return (
            f"<EmployeeChild(name={self.first_name!r} {self.last_name!r}, "
            f"birth_date={self.birth_date!r}, "
            f"eligible={self.is_tax_bonus_eligible!r})>"
        )
