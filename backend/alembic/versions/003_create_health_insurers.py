"""Create health_insurers table in shared schema.

Revision ID: 003
Revises: 002
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | Sequence[str] | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create shared.health_insurers table with UNIQUE constraint."""
    op.create_table(
        "health_insurers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "code",
            sa.String(length=4),
            nullable=False,
            comment="Insurer code (e.g. 24, 25, 27)",
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("iban", sa.String(length=34), nullable=False),
        sa.Column("bic", sa.String(length=11), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_health_insurers_code"),
        schema="shared",
    )


def downgrade() -> None:
    """Drop shared.health_insurers table."""
    op.drop_table("health_insurers", schema="shared")
