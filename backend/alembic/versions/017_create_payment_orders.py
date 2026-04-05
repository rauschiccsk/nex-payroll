"""Create payment_orders table.

Revision ID: 017
Revises: 016
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: str | Sequence[str] | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create payment_orders table with constraints and indexes."""
    op.create_table(
        "payment_orders",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # -- Foreign keys --
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to owning tenant",
        ),
        sa.Column(
            "employee_id",
            sa.UUID(),
            nullable=True,
            comment="Reference to employee (for net_wage type)",
        ),
        sa.Column(
            "health_insurer_id",
            sa.UUID(),
            nullable=True,
            comment="Reference to health insurer (for zp types)",
        ),
        # -- Period --
        sa.Column(
            "period_year",
            sa.Integer(),
            nullable=False,
            comment="Payroll period year",
        ),
        sa.Column(
            "period_month",
            sa.Integer(),
            nullable=False,
            comment="Payroll period month (1-12)",
        ),
        # -- Payment details --
        sa.Column(
            "payment_type",
            sa.String(length=30),
            nullable=False,
            comment="Type: net_wage, sp, zp_vszp, zp_dovera, zp_union, tax, pillar2",
        ),
        sa.Column(
            "recipient_name",
            sa.String(length=200),
            nullable=False,
            comment="Recipient (beneficiary) name",
        ),
        sa.Column(
            "recipient_iban",
            sa.String(length=34),
            nullable=False,
            comment="Recipient IBAN",
        ),
        sa.Column(
            "recipient_bic",
            sa.String(length=11),
            nullable=True,
            comment="Recipient BIC/SWIFT code",
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Payment amount in EUR",
        ),
        # -- Bank symbols --
        sa.Column(
            "variable_symbol",
            sa.String(length=10),
            nullable=True,
            comment="Variable symbol for bank transfer",
        ),
        sa.Column(
            "specific_symbol",
            sa.String(length=10),
            nullable=True,
            comment="Specific symbol for bank transfer",
        ),
        sa.Column(
            "constant_symbol",
            sa.String(length=4),
            nullable=True,
            comment="Constant symbol for bank transfer",
        ),
        sa.Column(
            "reference",
            sa.String(length=140),
            nullable=True,
            comment="SEPA end-to-end reference",
        ),
        # -- Status --
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="Order status: pending, exported, paid",
        ),
        # -- Timestamps --
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
        # -- Constraints --
        sa.CheckConstraint(
            "payment_type IN ('net_wage', 'sp', 'zp_vszp', 'zp_dovera', 'zp_union', 'tax', 'pillar2')",
            name="ck_payment_orders_payment_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'exported', 'paid')",
            name="ck_payment_orders_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_payment_orders_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_payment_orders_employee_id",
        ),
        sa.ForeignKeyConstraint(
            ["health_insurer_id"],
            ["shared.health_insurers.id"],
            name="fk_payment_orders_health_insurer_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("payment_orders") as batch_op:
        batch_op.create_index(
            "ix_payment_orders_tenant_period_type",
            ["tenant_id", "period_year", "period_month", "payment_type"],
            unique=False,
        )


def downgrade() -> None:
    """Drop payment_orders table."""
    op.drop_table("payment_orders")
