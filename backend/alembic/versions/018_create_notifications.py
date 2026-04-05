"""Create notifications table.

Revision ID: 018
Revises: 017
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: str | Sequence[str] | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create notifications table with constraints and indexes."""
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # -- Foreign keys --
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to owning tenant",
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to target user",
        ),
        # -- Notification content --
        sa.Column(
            "type",
            sa.String(length=50),
            nullable=False,
            comment="Notification type: deadline, anomaly, system, approval",
        ),
        sa.Column(
            "severity",
            sa.String(length=20),
            nullable=False,
            server_default="info",
            comment="Severity level: info, warning, critical",
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
            comment="Short notification title",
        ),
        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
            comment="Full notification message body",
        ),
        # -- Related entity (polymorphic reference) --
        sa.Column(
            "related_entity",
            sa.String(length=50),
            nullable=True,
            comment="Entity type name this notification relates to",
        ),
        sa.Column(
            "related_entity_id",
            sa.UUID(),
            nullable=True,
            comment="ID of the related entity",
        ),
        # -- Read tracking --
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether user has read this notification",
        ),
        sa.Column(
            "read_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when user read the notification",
        ),
        # -- Timestamps --
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
        # -- Constraints --
        sa.CheckConstraint(
            "type IN ('deadline', 'anomaly', 'system', 'approval')",
            name="ck_notifications_type",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_notifications_severity",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_notifications_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.create_index(
            "ix_notifications_tenant_user_is_read",
            ["tenant_id", "user_id", "is_read"],
            unique=False,
        )

    # DESC index requires raw SQL — batch_alter_table doesn't support
    # functional expressions in create_index
    op.execute("CREATE INDEX ix_notifications_tenant_created_at ON notifications (tenant_id, created_at DESC)")


def downgrade() -> None:
    """Drop notifications table."""
    op.drop_table("notifications")
