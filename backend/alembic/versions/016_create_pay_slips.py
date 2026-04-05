"""Create pay_slips table.

Revision ID: 016
Revises: 015
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: str | Sequence[str] | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create pay_slips table with constraints and indexes."""
    op.create_table(
        "pay_slips",
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
            "payroll_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to the approved payroll record",
        ),
        sa.Column(
            "employee_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to the employee",
        ),
        sa.Column(
            "period_year",
            sa.Integer(),
            nullable=False,
            comment="Pay slip period year (e.g. 2025)",
        ),
        sa.Column(
            "period_month",
            sa.Integer(),
            nullable=False,
            comment="Pay slip period month (1-12)",
        ),
        sa.Column(
            "pdf_path",
            sa.String(length=500),
            nullable=False,
            comment="Absolute path to generated PDF file",
        ),
        sa.Column(
            "file_size_bytes",
            sa.Integer(),
            nullable=True,
            comment="PDF file size in bytes",
        ),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp when the pay slip PDF was generated",
        ),
        sa.Column(
            "downloaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when employee first downloaded the pay slip",
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
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_pay_slips_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["payroll_id"],
            ["payrolls.id"],
            name="fk_pay_slips_payroll_id",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_pay_slips_employee_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "payroll_id",
            name="uq_pay_slips_tenant_payroll",
        ),
    )

    with op.batch_alter_table("pay_slips") as batch_op:
        batch_op.create_index(
            "ix_pay_slips_tenant_employee_period",
            ["tenant_id", "employee_id", "period_year", "period_month"],
            unique=False,
        )


def downgrade() -> None:
    """Drop pay_slips table."""
    op.drop_table("pay_slips")
