"""Create audit_log table in public schema.

Revision ID: 006
Revises: 005
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | Sequence[str] | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create public.audit_log table with indexes and CHECK constraint."""
    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Reference to tenant (public.tenants.id)"),
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=True,
            comment="User who performed the action (NULL for system actions)",
        ),
        sa.Column("action", sa.String(length=20), nullable=False, comment="Action type: CREATE, UPDATE, DELETE"),
        sa.Column("entity_type", sa.String(length=100), nullable=False, comment="Fully qualified entity/table name"),
        sa.Column("entity_id", sa.UUID(), nullable=False, comment="Primary key of the affected entity"),
        sa.Column(
            "old_values",
            sa.JSON(),
            nullable=True,
            comment="Entity state before the change (NULL for CREATE)",
        ),
        sa.Column(
            "new_values",
            sa.JSON(),
            nullable=True,
            comment="Entity state after the change (NULL for DELETE)",
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True, comment="Client IP address (IPv4 or IPv6)"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp when the audit record was created",
        ),
        sa.CheckConstraint(
            "action IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_audit_log_action",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["public.tenants.id"], name="fk_audit_log_tenant_id"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )

    with op.batch_alter_table("audit_log", schema="public") as batch_op:
        batch_op.create_index(
            "ix_audit_log_tenant_entity",
            ["tenant_id", "entity_type", "entity_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_audit_log_tenant_created",
            ["tenant_id", "created_at"],
            unique=False,
            postgresql_using="btree",
        )


def downgrade() -> None:
    """Drop public.audit_log table."""
    op.drop_table("audit_log", schema="public")
