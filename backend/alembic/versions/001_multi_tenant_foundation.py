"""Multi-tenant foundation — shared schema.

Creates the shared schema used by lookup tables (contribution_rates,
health_insurers, statutory_deadlines, tax_brackets).

Note: tenants table is created in 005_create_tenants.py and
users table is created in 012_create_users.py.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create shared schema for lookup tables."""
    op.execute("CREATE SCHEMA IF NOT EXISTS shared")


def downgrade() -> None:
    """Drop shared schema."""
    op.execute("DROP SCHEMA IF EXISTS shared CASCADE")
