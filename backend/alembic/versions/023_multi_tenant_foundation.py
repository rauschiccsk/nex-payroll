"""Multi-tenant foundation — add standalone lookup indexes on users.

Tables public.tenants and users were already created by migrations
005_create_tenants and 012_create_users respectively.  This migration
adds standalone indexes on users.tenant_id, users.email and
users.username to accelerate FK look-ups and login queries that do not
use the existing composite unique constraints.

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
    """Add standalone lookup indexes on users table."""
    # Standalone index on tenant_id for FK performance
    # (ix_users_tenant_role covers tenant_id+role; this is for tenant_id alone)
    op.create_index(
        "ix_users_tenant_id",
        "users",
        ["tenant_id"],
    )

    # Standalone index on email for direct login lookups
    # (uq_users_tenant_email is composite tenant_id+email)
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
    )

    # Standalone index on username for direct login lookups
    # (uq_users_tenant_username is composite tenant_id+username)
    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
    )


def downgrade() -> None:
    """Drop standalone lookup indexes."""
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
