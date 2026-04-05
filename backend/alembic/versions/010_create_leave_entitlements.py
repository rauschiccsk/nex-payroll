"""Create leave_entitlements table.

Revision ID: 010
Revises: 009
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: str | Sequence[str] | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create leave_entitlements table with constraints and indexes."""
    op.create_table(
        "leave_entitlements",
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
            nullable=False,
            comment="Reference to employee",
        ),
        sa.Column(
            "year",
            sa.Integer(),
            nullable=False,
            comment="Calendar year of the entitlement",
        ),
        sa.Column(
            "total_days",
            sa.Integer(),
            nullable=False,
            comment="Total annual leave days entitled",
        ),
        sa.Column(
            "used_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of leave days already used",
        ),
        sa.Column(
            "remaining_days",
            sa.Integer(),
            nullable=False,
            comment="Remaining leave days (computed: total - used)",
        ),
        sa.Column(
            "carryover_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Leave days carried over from previous year",
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
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_leave_entitlements_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_leave_entitlements_employee_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "employee_id",
            "year",
            name="uq_leave_entitlements_tenant_employee_year",
        ),
    )


def downgrade() -> None:
    """Drop leave_entitlements table."""
    op.drop_table("leave_entitlements")
