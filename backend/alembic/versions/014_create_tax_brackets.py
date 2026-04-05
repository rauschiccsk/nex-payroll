"""Create tax_brackets table in shared schema.

Revision ID: 014
Revises: 013
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: str | Sequence[str] | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create shared.tax_brackets table with index."""
    op.create_table(
        "tax_brackets",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "bracket_order",
            sa.Integer(),
            nullable=False,
            comment="Order of tax bracket (1=lowest rate first)",
        ),
        sa.Column(
            "min_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Minimum taxable income for this bracket",
        ),
        sa.Column(
            "max_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
            comment="Maximum taxable income for this bracket (NULL=unlimited)",
        ),
        sa.Column(
            "rate_percent",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            comment="Tax rate in percent (e.g. 19.00, 25.00)",
        ),
        sa.Column(
            "nczd_annual",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Annual NCZD (nezdanitelna cast zakladu dane)",
        ),
        sa.Column(
            "nczd_monthly",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Monthly NCZD (1/12 of annual)",
        ),
        sa.Column(
            "nczd_reduction_threshold",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Income threshold above which NCZD is reduced",
        ),
        sa.Column(
            "nczd_reduction_formula",
            sa.String(length=100),
            nullable=False,
            comment="Formula for NCZD reduction (e.g. '44.2 * ZM - ZD')",
        ),
        sa.Column(
            "valid_from",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "valid_to",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="shared",
    )

    with op.batch_alter_table("tax_brackets", schema="shared") as batch_op:
        batch_op.create_index(
            "ix_tax_brackets_valid_from_bracket_order",
            ["valid_from", "bracket_order"],
            unique=False,
        )


def downgrade() -> None:
    """Drop shared.tax_brackets table."""
    with op.batch_alter_table("tax_brackets", schema="shared") as batch_op:
        batch_op.drop_index("ix_tax_brackets_valid_from_bracket_order")

    op.drop_table("tax_brackets", schema="shared")
