"""Multi-tenant foundation — extend tenants + users for superadmin support.

Tenants: widen ico/dic/ic_dph/address_street columns, add contact_email.
Users: make tenant_id nullable, add superadmin role, add check constraint
  that tenant_id IS NULL only when role='superadmin'.
Add explicit indexes on users(tenant_id), users(email), users(username).

Revision ID: 023
Revises: 022
Create Date: 2026-04-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023"
down_revision: str | Sequence[str] | None = "022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Extend tenants and users tables for multi-tenant foundation."""
    # -- Tenants: widen columns and add contact_email --
    with op.batch_alter_table("tenants", schema="public") as batch_op:
        batch_op.alter_column(
            "ico",
            existing_type=sa.String(8),
            type_=sa.String(20),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "dic",
            existing_type=sa.String(12),
            type_=sa.String(20),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "ic_dph",
            existing_type=sa.String(14),
            type_=sa.String(20),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "address_street",
            existing_type=sa.String(200),
            type_=sa.String(255),
            existing_nullable=False,
        )
        batch_op.add_column(
            sa.Column(
                "contact_email",
                sa.String(255),
                nullable=True,
                comment="Primary contact email for tenant",
            ),
        )

    # -- Users: make tenant_id nullable for superadmin --
    with op.batch_alter_table("users", schema="public") as batch_op:
        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.UUID(),
            nullable=True,
        )

        # Drop old role CHECK, add new one with superadmin
        batch_op.drop_constraint("ck_users_role", type_="check")

    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('superadmin', 'director', 'accountant', 'employee')",
        schema="public",
    )

    # Constraint: tenant_id NULL only if role='superadmin'
    op.create_check_constraint(
        "ck_users_superadmin_no_tenant",
        "users",
        "(role = 'superadmin' AND tenant_id IS NULL) OR (role != 'superadmin' AND tenant_id IS NOT NULL)",
        schema="public",
    )

    # Explicit indexes on users
    with op.batch_alter_table("users", schema="public") as batch_op:
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
    """Revert multi-tenant foundation changes."""
    # Drop new indexes
    with op.batch_alter_table("users", schema="public") as batch_op:
        batch_op.drop_index("ix_users_username")
        batch_op.drop_index("ix_users_email")
        batch_op.drop_index("ix_users_tenant_id")

    # Drop superadmin constraint
    op.drop_constraint("ck_users_superadmin_no_tenant", "users", type_="check")

    # Revert role CHECK to original
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('director', 'accountant', 'employee')",
        schema="public",
    )

    # Make tenant_id NOT NULL again
    with op.batch_alter_table("users", schema="public") as batch_op:
        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.UUID(),
            nullable=False,
        )

    # Revert tenants changes
    with op.batch_alter_table("tenants", schema="public") as batch_op:
        batch_op.drop_column("contact_email")
        batch_op.alter_column(
            "address_street",
            existing_type=sa.String(255),
            type_=sa.String(200),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "ic_dph",
            existing_type=sa.String(20),
            type_=sa.String(14),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "dic",
            existing_type=sa.String(20),
            type_=sa.String(12),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "ico",
            existing_type=sa.String(20),
            type_=sa.String(8),
            existing_nullable=False,
        )
