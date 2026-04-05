"""Employee model — company employee record.

Schema: tenant-specific
Contains personal data, employment info, and references to health insurer.
PII fields (birth_number, bank_iban) are encrypted at rest using Fernet (AES-256).
"""

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
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
from app.models.types import EncryptedString


class Employee(UUIDMixin, TimestampMixin, Base):
    """Employee belonging to a specific tenant.

    Tenant-specific table — lives in the tenant's dedicated schema.
    PII fields (birth_number, bank_iban) are encrypted with Fernet (AES-256).
    Soft-delete via is_deleted flag.
    """

    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "employee_number",
            name="uq_employees_tenant_employee_number",
        ),
        CheckConstraint(
            "gender IN ('M', 'F')",
            name="ck_employees_gender",
        ),
        CheckConstraint(
            "tax_declaration_type IN ('standard', 'secondary', 'none')",
            name="ck_employees_tax_declaration_type",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'terminated')",
            name="ck_employees_status",
        ),
        Index("ix_employees_tenant_status", "tenant_id", "status"),
        Index("ix_employees_tenant_last_name", "tenant_id", "last_name"),
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        comment="Reference to owning tenant",
    )

    # -- Identification --

    employee_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Unique employee number within tenant",
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="First name",
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Last name",
    )

    title_before: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Academic title before name (e.g. Ing., Mgr.)",
    )

    title_after: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Academic title after name (e.g. PhD., CSc.)",
    )

    # -- Personal data --

    birth_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date of birth",
    )

    birth_number: Mapped[str] = mapped_column(
        EncryptedString(),
        nullable=False,
        comment="Slovak birth number (rodné číslo) — encrypted at rest",
    )

    gender: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
        comment="Gender: M or F",
    )

    nationality: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        server_default="SK",
        comment="ISO 3166-1 alpha-2 nationality code",
    )

    # -- Address --

    address_street: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Street address",
    )

    address_city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="City",
    )

    address_zip: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="ZIP / postal code",
    )

    address_country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        server_default="SK",
        comment="ISO 3166-1 alpha-2 country code",
    )

    # -- Banking --

    bank_iban: Mapped[str] = mapped_column(
        EncryptedString(),
        nullable=False,
        comment="Employee bank account IBAN — encrypted at rest",
    )

    bank_bic: Mapped[str | None] = mapped_column(
        String(11),
        nullable=True,
        comment="Bank BIC/SWIFT code",
    )

    # -- Insurance & Tax --

    health_insurer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shared.health_insurers.id"),
        nullable=False,
        comment="Reference to health insurance company",
    )

    tax_declaration_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Tax declaration: standard, secondary, none",
    )

    nczd_applied: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether NČZD (non-taxable amount) is applied",
    )

    pillar2_saver: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether employee is a 2nd pillar saver",
    )

    is_disabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether employee has a disability status",
    )

    # -- Employment status --

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="active",
        comment="Employment status: active, inactive, terminated",
    )

    hire_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date of hire",
    )

    termination_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date of employment termination (NULL if still employed)",
    )

    # -- Soft delete --

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Soft-delete flag",
    )

    def __repr__(self) -> str:
        return (
            f"<Employee(employee_number={self.employee_number!r}, "
            f"name={self.first_name!r} {self.last_name!r}, "
            f"status={self.status!r})>"
        )
