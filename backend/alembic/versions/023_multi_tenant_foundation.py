"""Multi-tenant foundation — alter tenants + users for multi-tenant support.

Widen tenants columns (ico, dic, ic_dph, address_street) per task spec,
add contact_email column, make users.tenant_id nullable for superadmin role,
update role check constraint to include 'superadmin', add superadmin/tenant
check constraint, and add explicit indexes on users table.

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
    """Alter tenants and users tables for multi-tenant foundation."""
    # --- Tenants: widen columns and add contact_email ---
    with op.batch_alter_table("tenants", schema="public") as batch_op:
        batch_op.alter_column(
            "ico",
            existing_type=sa.String(length=8),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "dic",
            existing_type=sa.String(length=12),
            type_=sa.String(length=20),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "ic_dph",
            existing_type=sa.String(length=14),
            type_=sa.String(length=20),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "address_street",
            existing_type=sa.String(length=200),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
        batch_op.add_column(
            sa.Column(
                "contact_email",
                sa.String(length=255),
                nullable=True,
                comment="Primary contact email for tenant",
            ),
        )

    # --- Users: make tenant_id nullable, update check constraints, add indexes ---
    with op.batch_alter_table("users", schema="public") as batch_op:
        # Make tenant_id nullable (required for superadmin users)
        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.UUID(),
            nullable=True,
            comment="Reference to owning tenant (NULL for superadmin)",
        )

        # Drop old role check constraint and replace with one including superadmin
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('superadmin', 'director', 'accountant', 'employee')",
        )

        # Add superadmin/tenant_id business rule constraint
        batch_op.create_check_constraint(
            "ck_users_superadmin_no_tenant",
            "(role = 'superadmin' AND tenant_id IS NULL) OR "
            "(role != 'superadmin' AND tenant_id IS NOT NULL)",
        )

        # Add explicit single-column indexes for performance
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
    # --- Users: revert indexes, constraints, tenant_id nullability ---
    with op.batch_alter_table("users", schema="public") as batch_op:
        batch_op.drop_index("ix_users_username")
        batch_op.drop_index("ix_users_email")
        batch_op.drop_index("ix_users_tenant_id")

        batch_op.drop_constraint("ck_users_superadmin_no_tenant", type_="check")

        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('director', 'accountant', 'employee')",
        )

        batch_op.alter_column(
            "tenant_id",
            existing_type=sa.UUID(),
            nullable=False,
            comment="Reference to owning tenant",
        )

    # --- Tenants: revert column widths and drop contact_email ---
    with op.batch_alter_table("tenants", schema="public") as batch_op:
        batch_op.drop_column("contact_email")
        batch_op.alter_column(
            "address_street",
            existing_type=sa.String(length=255),
            type_=sa.String(length=200),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "ic_dph",
            existing_type=sa.String(length=20),
            type_=sa.String(length=14),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "dic",
            existing_type=sa.String(length=20),
            type_=sa.String(length=12),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "ico",
            existing_type=sa.String(length=20),
            type_=sa.String(length=8),
            existing_nullable=False,
        )
