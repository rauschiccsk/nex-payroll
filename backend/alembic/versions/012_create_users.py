"""Create users table.

Revision ID: 012
Revises: 011
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | Sequence[str] | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create users table with constraints and indexes."""
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
            nullable=False,
            comment="Reference to owning tenant",
        ),
        sa.Column(
            "employee_id",
            sa.UUID(),
            nullable=True,
            comment="Optional link to employee record (required for role='employee')",
        ),
        sa.Column(
            "username",
            sa.String(length=100),
            nullable=False,
            comment="Login username (unique within tenant)",
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
            comment="Email address (unique within tenant)",
        ),
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
            comment="Argon2 password hash via pwdlib",
        ),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            comment="User role: director, accountant, employee",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Soft-delete flag (False = deactivated user)",
        ),
        sa.Column(
            "last_login_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp of last successful login",
        ),
        sa.Column(
            "password_changed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp of last password change",
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
            "role IN ('director', 'accountant', 'employee')",
            name="ck_users_role",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_users_tenant_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_users_employee_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "username",
            name="uq_users_tenant_username",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "email",
            name="uq_users_tenant_email",
        ),
    )

    # Partial unique index: UNIQUE(employee_id) WHERE employee_id IS NOT NULL
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index(
            "uq_users_employee_id",
            ["employee_id"],
            unique=True,
            postgresql_where=sa.text("employee_id IS NOT NULL"),
        )
        batch_op.create_index(
            "ix_users_tenant_role",
            ["tenant_id", "role"],
            unique=False,
        )


def downgrade() -> None:
    """Drop users table."""
    op.drop_table("users")
