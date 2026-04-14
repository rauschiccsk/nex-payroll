"""Multi-tenant foundation — tenants table + users table.

Creates the public.tenants and public.users tables with full column
definitions, indexes and constraints for multi-tenant support.

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
    """Create public.tenants and public.users tables."""
    # -- public.tenants --
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("ico", sa.String(length=20), nullable=False),
        sa.Column("dic", sa.String(length=20), nullable=True),
        sa.Column("ic_dph", sa.String(length=20), nullable=True),
        sa.Column("address_street", sa.String(length=255), nullable=False),
        sa.Column("address_city", sa.String(length=100), nullable=False),
        sa.Column("address_zip", sa.String(length=10), nullable=False),
        sa.Column(
            "address_country",
            sa.String(length=2),
            nullable=False,
            server_default="SK",
        ),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("bank_iban", sa.String(length=34), nullable=False),
        sa.Column("bank_bic", sa.String(length=11), nullable=True),
        sa.Column("schema_name", sa.String(length=63), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schema_name", name="uq_mt_tenants_schema_name"),
        schema="public",
    )

    # -- public.users --
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "last_login_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('superadmin', 'director', 'accountant', 'employee')",
            name="ck_mt_users_role",
        ),
        sa.CheckConstraint(
            "(role = 'superadmin' AND tenant_id IS NULL)"
            " OR (role != 'superadmin' AND tenant_id IS NOT NULL)",
            name="ck_mt_users_superadmin_no_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_mt_users_tenant_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_mt_users_username"),
        sa.UniqueConstraint("email", name="uq_mt_users_email"),
        schema="public",
    )

    # Indexes on public.users
    op.create_index(
        "ix_mt_users_tenant_id",
        "users",
        ["tenant_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_mt_users_email",
        "users",
        ["email"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_mt_users_username",
        "users",
        ["username"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    """Drop public.users and public.tenants tables."""
    op.drop_table("users", schema="public")
    op.drop_table("tenants", schema="public")
