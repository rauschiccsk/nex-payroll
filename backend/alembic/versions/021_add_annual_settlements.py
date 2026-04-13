"""add_annual_settlements_table

Revision ID: 021
Revises: 020
Create Date: 2026-04-13 15:22:46.288138

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021"
down_revision: str | Sequence[str] | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "annual_settlements",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to owning tenant",
        ),
        sa.Column(
            "employee_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to employee",
        ),
        sa.Column(
            "year",
            sa.Integer(),
            nullable=False,
            comment="Settlement year (e.g. 2026)",
        ),
        sa.Column(
            "total_gross_wage",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Total annual gross wage (sum of monthly gross wages)",
        ),
        sa.Column(
            "total_sp_employee",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Total annual SP employee contributions",
        ),
        sa.Column(
            "total_zp_employee",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Total annual ZP employee contributions",
        ),
        sa.Column(
            "annual_partial_tax_base",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Annual partial tax base (gross - SP - ZP)",
        ),
        sa.Column(
            "nczd_monthly_total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Sum of monthly NCZD applied during the year",
        ),
        sa.Column(
            "nczd_annual_recalculated",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Recalculated annual NCZD using annual rules",
        ),
        sa.Column(
            "annual_tax_base",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Annual tax base (partial_tax_base - annual NCZD)",
        ),
        sa.Column(
            "annual_tax_19",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Tax at 19% rate (on amount up to threshold)",
        ),
        sa.Column(
            "annual_tax_25",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
            comment="Tax at 25% rate (on amount above threshold)",
        ),
        sa.Column(
            "annual_tax_total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Total annual tax liability (19% + 25%)",
        ),
        sa.Column(
            "annual_child_bonus",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
            comment="Total annual child tax bonus",
        ),
        sa.Column(
            "annual_tax_after_bonus",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Annual tax after child bonus deduction",
        ),
        sa.Column(
            "total_monthly_advances",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Sum of monthly tax advances paid during the year",
        ),
        sa.Column(
            "settlement_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Settlement: positive=overpaid (refund), negative=underpaid",
        ),
        sa.Column(
            "months_count",
            sa.Integer(),
            nullable=False,
            comment="Number of payroll months included in settlement",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="calculated",
            nullable=False,
            comment="Settlement status: calculated, approved, paid",
        ),
        sa.Column(
            "calculated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when settlement was calculated",
        ),
        sa.Column(
            "approved_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when settlement was approved",
        ),
        sa.Column(
            "approved_by",
            sa.UUID(),
            nullable=True,
            comment="User who approved the settlement",
        ),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
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
            "status IN ('calculated', 'approved', 'paid')",
            name="ck_annual_settlements_status",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "employee_id",
            "year",
            name="uq_annual_settlements_tenant_employee_year",
        ),
    )
    with op.batch_alter_table("annual_settlements", schema=None) as batch_op:
        batch_op.create_index(
            "ix_annual_settlements_tenant_year",
            ["tenant_id", "year"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("annual_settlements", schema=None) as batch_op:
        batch_op.drop_index("ix_annual_settlements_tenant_year")

    op.drop_table("annual_settlements")
