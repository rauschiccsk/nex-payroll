"""Tenant model — company/organization.

Schema: public
Each tenant represents a separate company using NEX Payroll.
Tenant's schema_name determines the PostgreSQL schema for tenant-specific data.
"""

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(UUIDMixin, TimestampMixin, Base):
    """Company / organization registered in NEX Payroll.

    Lives in the 'public' schema.
    Each tenant has a dedicated PostgreSQL schema (schema_name)
    that holds all tenant-specific tables (employees, payrolls, etc.).
    """

    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("ico", name="uq_tenants_ico"),
        UniqueConstraint("schema_name", name="uq_tenants_schema_name"),
        {"schema": "public", "extend_existing": True},
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Company legal name",
    )

    ico: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Company registration number (IČO)",
    )

    dic: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Tax identification number (DIČ)",
    )

    ic_dph: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="VAT identification number (IČ DPH)",
    )

    address_street: Mapped[str] = mapped_column(
        String(255),
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

    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Primary contact email for tenant",
    )

    bank_iban: Mapped[str] = mapped_column(
        String(34),
        nullable=False,
        comment="Company bank account IBAN",
    )

    bank_bic: Mapped[str | None] = mapped_column(
        String(11),
        nullable=True,
        comment="Bank BIC/SWIFT code",
    )

    schema_name: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        comment="PostgreSQL schema name for tenant-specific data",
    )

    default_role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="accountant",
        comment="Default role assigned to new users in this tenant",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Soft-delete flag",
    )

    def __repr__(self) -> str:
        return (
            f"<Tenant(name={self.name!r}, "
            f"ico={self.ico!r}, "
            f"schema_name={self.schema_name!r}, "
            f"is_active={self.is_active})>"
        )
