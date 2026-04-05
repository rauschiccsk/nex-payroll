"""Create employees table.

Revision ID: 007
Revises: 006
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | Sequence[str] | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create employees table with constraints and indexes."""
    op.create_table(
        "employees",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to owning tenant",
        ),
        sa.Column(
            "employee_number",
            sa.String(length=20),
            nullable=False,
            comment="Unique employee number within tenant",
        ),
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
            comment="First name",
        ),
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=False,
            comment="Last name",
        ),
        sa.Column(
            "title_before",
            sa.String(length=50),
            nullable=True,
            comment="Academic title before name (e.g. Ing., Mgr.)",
        ),
        sa.Column(
            "title_after",
            sa.String(length=50),
            nullable=True,
            comment="Academic title after name (e.g. PhD., CSc.)",
        ),
        sa.Column(
            "birth_date",
            sa.Date(),
            nullable=False,
            comment="Date of birth",
        ),
        sa.Column(
            "birth_number",
            sa.Text(),
            nullable=False,
            comment="Slovak birth number (rodné číslo) — encrypted at rest",
        ),
        sa.Column(
            "gender",
            sa.String(length=1),
            nullable=False,
            comment="Gender: M or F",
        ),
        sa.Column(
            "nationality",
            sa.String(length=2),
            nullable=False,
            server_default="SK",
            comment="ISO 3166-1 alpha-2 nationality code",
        ),
        sa.Column(
            "address_street",
            sa.String(length=200),
            nullable=False,
            comment="Street address",
        ),
        sa.Column(
            "address_city",
            sa.String(length=100),
            nullable=False,
            comment="City",
        ),
        sa.Column(
            "address_zip",
            sa.String(length=10),
            nullable=False,
            comment="ZIP / postal code",
        ),
        sa.Column(
            "address_country",
            sa.String(length=2),
            nullable=False,
            server_default="SK",
            comment="ISO 3166-1 alpha-2 country code",
        ),
        sa.Column(
            "bank_iban",
            sa.Text(),
            nullable=False,
            comment="Employee bank account IBAN — encrypted at rest",
        ),
        sa.Column(
            "bank_bic",
            sa.String(length=11),
            nullable=True,
            comment="Bank BIC/SWIFT code",
        ),
        sa.Column(
            "health_insurer_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to health insurance company",
        ),
        sa.Column(
            "tax_declaration_type",
            sa.String(length=20),
            nullable=False,
            comment="Tax declaration: standard, secondary, none",
        ),
        sa.Column(
            "nczd_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether NČZD (non-taxable amount) is applied",
        ),
        sa.Column(
            "pillar2_saver",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether employee is a 2nd pillar saver",
        ),
        sa.Column(
            "is_disabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether employee has a disability status",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
            comment="Employment status: active, inactive, terminated",
        ),
        sa.Column(
            "hire_date",
            sa.Date(),
            nullable=False,
            comment="Date of hire",
        ),
        sa.Column(
            "termination_date",
            sa.Date(),
            nullable=True,
            comment="Date of employment termination (NULL if still employed)",
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Soft-delete flag",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "gender IN ('M', 'F')",
            name="ck_employees_gender",
        ),
        sa.CheckConstraint(
            "tax_declaration_type IN ('standard', 'secondary', 'none')",
            name="ck_employees_tax_declaration_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'terminated')",
            name="ck_employees_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_employees_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["health_insurer_id"],
            ["shared.health_insurers.id"],
            name="fk_employees_health_insurer_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "employee_number",
            name="uq_employees_tenant_employee_number",
        ),
    )

    with op.batch_alter_table("employees") as batch_op:
        batch_op.create_index(
            "ix_employees_tenant_status",
            ["tenant_id", "status"],
            unique=False,
        )
        batch_op.create_index(
            "ix_employees_tenant_last_name",
            ["tenant_id", "last_name"],
            unique=False,
        )


def downgrade() -> None:
    """Drop employees table."""
    op.drop_table("employees")
