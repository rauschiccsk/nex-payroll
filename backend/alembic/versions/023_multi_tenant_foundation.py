"""Multi-tenant foundation — tenants + users tables.

Creates the foundational public.tenants and public.users tables
for multi-tenant support.

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
    # public.tenants table
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("ico", sa.String(length=20), nullable=True),
        sa.Column("dic", sa.String(length=20), nullable=True),
        sa.Column("ic_dph", sa.String(length=20), nullable=True),
        sa.Column("address_street", sa.String(length=255), nullable=True),
        sa.Column("address_city", sa.String(length=100), nullable=True),
        sa.Column("address_zip", sa.String(length=10), nullable=True),
        sa.Column(
            "address_country",
            sa.String(length=2),
            nullable=True,
        ),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("bank_iban", sa.String(length=34), nullable=True),
        sa.Column("bank_bic", sa.String(length=11), nullable=True),
        sa.Column(
            "schema_name",
            sa.String(length=63),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
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

    # public.users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=True,
        ),
        sa.Column(
            "username",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
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
            "(role = 'superadmin') OR (tenant_id IS NOT NULL)",
            name="ck_mt_users_tenant_id_null_superadmin",
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

    # Index on users.tenant_id (email and username already indexed via UniqueConstraint)
    op.create_index(
        "ix_mt_users_tenant_id",
        "users",
        ["tenant_id"],
        schema="public",
    )


def downgrade() -> None:
    """Drop users and tenants tables."""
    op.drop_index("ix_mt_users_tenant_id", table_name="users", schema="public")
    op.drop_table("users", schema="public")
    op.drop_table("tenants", schema="public")
