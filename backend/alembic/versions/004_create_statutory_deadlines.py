"""Create statutory_deadlines table in shared schema.

Revision ID: 004
Revises: 003
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | Sequence[str] | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create shared.statutory_deadlines table with CHECK constraint and indexes."""
    op.create_table(
        "statutory_deadlines",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "deadline_type",
            sa.String(length=30),
            nullable=False,
            comment="Type: sp_monthly, zp_monthly, tax_advance, tax_reconciliation, sp_annual, zp_annual",
        ),
        sa.Column(
            "institution",
            sa.String(length=100),
            nullable=False,
            comment="Target institution (e.g. Sociálna poisťovňa, VšZP, DÚ)",
        ),
        sa.Column(
            "day_of_month",
            sa.Integer(),
            nullable=False,
            comment="Day of month the deadline falls on",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            comment="Human-readable description (Slovak)",
        ),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "deadline_type IN ("
            "'sp_monthly', 'zp_monthly', 'tax_advance', "
            "'tax_reconciliation', 'sp_annual', 'zp_annual')",
            name="ck_statutory_deadlines_deadline_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="shared",
    )
    with op.batch_alter_table("statutory_deadlines", schema="shared") as batch_op:
        batch_op.create_index("ix_statutory_deadlines_deadline_type", ["deadline_type"], unique=False)
        batch_op.create_index("ix_statutory_deadlines_valid_from", ["valid_from"], unique=False)


def downgrade() -> None:
    """Drop shared.statutory_deadlines table."""
    with op.batch_alter_table("statutory_deadlines", schema="shared") as batch_op:
        batch_op.drop_index("ix_statutory_deadlines_valid_from")
        batch_op.drop_index("ix_statutory_deadlines_deadline_type")

    op.drop_table("statutory_deadlines", schema="shared")
