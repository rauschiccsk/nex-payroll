"""Create contribution_rates table in shared schema.

Revision ID: 002
Revises: 001
Create Date: 2026-04-04 22:58:34.346853

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | Sequence[str] | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create shared.contribution_rates table with CHECK constraint and composite index."""
    op.create_table(
        "contribution_rates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "rate_type",
            sa.String(length=50),
            nullable=False,
            comment="e.g. sp_employee_nemocenske, zp_employee",
        ),
        sa.Column("rate_percent", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("max_assessment_base", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("payer", sa.String(length=20), nullable=False, comment="employee or employer"),
        sa.Column("fund", sa.String(length=50), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("payer IN ('employee', 'employer')", name="ck_contribution_rates_payer"),
        sa.PrimaryKeyConstraint("id"),
        schema="shared",
    )
    with op.batch_alter_table("contribution_rates", schema="shared") as batch_op:
        batch_op.create_index("ix_contribution_rates_rate_type_valid_from", ["rate_type", "valid_from"], unique=False)


def downgrade() -> None:
    """Drop shared.contribution_rates table."""
    with op.batch_alter_table("contribution_rates", schema="shared") as batch_op:
        batch_op.drop_index("ix_contribution_rates_rate_type_valid_from")

    op.drop_table("contribution_rates", schema="shared")
