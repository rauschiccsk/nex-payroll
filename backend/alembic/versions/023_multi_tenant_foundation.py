"""Multi-tenant foundation — add standalone indexes on users table.

Tenants (005) and users (012) tables already exist with DESIGN.md-compliant
schema. This migration adds standalone single-column indexes on users for
direct lookups by tenant_id, email, and username (complementing the existing
compound unique constraints from 012).

Revision ID: 023
Revises: 022
Create Date: 2026-04-14 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023"
down_revision: str | Sequence[str] | None = "022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add standalone indexes on users.tenant_id, users.email, users.username."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(
            "ix_users_tenant_id",
            ["tenant_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_users_email",
            ["email"],
            unique=False,
        )
        batch_op.create_index(
            "ix_users_username",
            ["username"],
            unique=False,
        )


def downgrade() -> None:
    """Remove standalone indexes from users table."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_username")
        batch_op.drop_index("ix_users_email")
        batch_op.drop_index("ix_users_tenant_id")
