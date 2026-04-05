"""Create tenants table in public schema.

Revision ID: 005
Revises: 004
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | Sequence[str] | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create public.tenants table with UNIQUE constraints."""
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, comment="Company legal name"),
        sa.Column(
            "ico",
            sa.String(length=8),
            nullable=False,
            comment="Company registration number (IČO)",
        ),
        sa.Column("dic", sa.String(length=12), nullable=True, comment="Tax identification number (DIČ)"),
        sa.Column("ic_dph", sa.String(length=14), nullable=True, comment="VAT identification number (IČ DPH)"),
        sa.Column("address_street", sa.String(length=200), nullable=False, comment="Street address"),
        sa.Column("address_city", sa.String(length=100), nullable=False, comment="City"),
        sa.Column("address_zip", sa.String(length=10), nullable=False, comment="ZIP / postal code"),
        sa.Column(
            "address_country",
            sa.String(length=2),
            nullable=False,
            server_default="SK",
            comment="ISO 3166-1 alpha-2 country code",
        ),
        sa.Column("bank_iban", sa.String(length=34), nullable=False, comment="Company bank account IBAN"),
        sa.Column("bank_bic", sa.String(length=11), nullable=True, comment="Bank BIC/SWIFT code"),
        sa.Column(
            "schema_name",
            sa.String(length=63),
            nullable=False,
            comment="PostgreSQL schema name for tenant-specific data",
        ),
        sa.Column(
            "default_role",
            sa.String(length=20),
            nullable=False,
            server_default="accountant",
            comment="Default role assigned to new users in this tenant",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Soft-delete flag",
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ico", name="uq_tenants_ico"),
        sa.UniqueConstraint("schema_name", name="uq_tenants_schema_name"),
        schema="public",
    )


def downgrade() -> None:
    """Drop public.tenants table."""
    op.drop_table("tenants", schema="public")
