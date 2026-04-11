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
    """Create shared.statutory_deadlines table with CHECK constraint, indexes, and seed data."""
    op.create_table(
        "statutory_deadlines",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "code",
            sa.String(length=50),
            nullable=False,
            comment="Unique code identifier (e.g. SP_MONTHLY, ZP_MONTHLY)",
        ),
        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
            comment="Human-readable name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional longer description (Slovak)",
        ),
        sa.Column(
            "deadline_type",
            sa.String(length=20),
            nullable=False,
            comment="Type: monthly, annual, one_time",
        ),
        sa.Column(
            "day_of_month",
            sa.Integer(),
            nullable=True,
            comment="Day of month the deadline falls on (NULL if not applicable)",
        ),
        sa.Column(
            "month_of_year",
            sa.Integer(),
            nullable=True,
            comment="Month of year for annual deadlines (1-12, NULL for monthly)",
        ),
        sa.Column(
            "business_days_rule",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="If true, deadline shifts to next business day",
        ),
        sa.Column(
            "institution",
            sa.String(length=100),
            nullable=False,
            comment="Target institution (e.g. Socialna poistovna, VsZP, DU)",
        ),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "deadline_type IN ('monthly', 'annual', 'one_time')",
            name="ck_statutory_deadlines_deadline_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_statutory_deadlines_code"),
        schema="shared",
    )
    with op.batch_alter_table("statutory_deadlines", schema="shared") as batch_op:
        batch_op.create_index("ix_statutory_deadlines_deadline_type", ["deadline_type"], unique=False)
        batch_op.create_index("ix_statutory_deadlines_valid_from", ["valid_from"], unique=False)

    # Seed data per DESIGN.md Section 5.18
    op.execute(
        sa.text(
            """
            INSERT INTO shared.statutory_deadlines
                (code, name, deadline_type, day_of_month, month_of_year,
                 business_days_rule, institution, valid_from)
            VALUES
                ('SP_MONTHLY', 'Mesačný výkaz SP', 'monthly', 20, NULL,
                 false, 'Sociálna poisťovňa', '2025-01-01'),
                ('ZP_MONTHLY', 'Mesačný prehľad ZP', 'monthly', 3, NULL,
                 true, 'Zdravotná poisťovňa', '2025-01-01'),
                ('TAX_MONTHLY', 'Preddavok dane', 'monthly', NULL, NULL,
                 false, 'Daňový úrad', '2025-01-01'),
                ('TAX_ANNUAL', 'Hlásenie o dani (ročné)', 'annual', 30, 4,
                 false, 'Daňový úrad', '2025-01-01'),
                ('CERT_ANNUAL', 'Potvrdenie o príjmoch', 'annual', 10, 3,
                 false, 'Zamestnávateľ', '2025-01-01'),
                ('ELDP_ANNUAL', 'ELDP', 'annual', 30, 4,
                 false, 'Sociálna poisťovňa', '2025-01-01')
            """
        )
    )


def downgrade() -> None:
    """Drop shared.statutory_deadlines table."""
    with op.batch_alter_table("statutory_deadlines", schema="shared") as batch_op:
        batch_op.drop_index("ix_statutory_deadlines_valid_from")
        batch_op.drop_index("ix_statutory_deadlines_deadline_type")

    op.drop_table("statutory_deadlines", schema="shared")
