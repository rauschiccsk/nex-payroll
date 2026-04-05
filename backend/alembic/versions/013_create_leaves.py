"""Create leaves table.

Revision ID: 013
Revises: 012
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: str | Sequence[str] | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create leaves table with constraints and indexes."""
    op.create_table(
        "leaves",
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
            "approved_by",
            sa.UUID(),
            nullable=True,
            comment="User who approved/rejected the leave request",
        ),
        sa.Column(
            "leave_type",
            sa.String(length=30),
            nullable=False,
            comment=("Leave type: annual, sick_employer, sick_sp, ocr, maternity, parental, unpaid, obstacle"),
        ),
        sa.Column(
            "start_date",
            sa.Date(),
            nullable=False,
            comment="First day of leave",
        ),
        sa.Column(
            "end_date",
            sa.Date(),
            nullable=False,
            comment="Last day of leave",
        ),
        sa.Column(
            "business_days",
            sa.Integer(),
            nullable=False,
            comment="Number of business (working) days in the leave period",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="Leave status: pending, approved, rejected, cancelled",
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=True,
            comment="Optional note or reason for the leave request",
        ),
        sa.Column(
            "approved_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when the leave was approved/rejected",
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
            "leave_type IN ('annual', 'sick_employer', 'sick_sp', "
            "'ocr', 'maternity', 'parental', 'unpaid', 'obstacle')",
            name="ck_leaves_leave_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'cancelled')",
            name="ck_leaves_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_leaves_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_leaves_employee_id",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_leaves_approved_by",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("leaves") as batch_op:
        batch_op.create_index(
            "ix_leaves_tenant_employee_start",
            ["tenant_id", "employee_id", "start_date"],
            unique=False,
        )
        batch_op.create_index(
            "ix_leaves_tenant_status",
            ["tenant_id", "status"],
            unique=False,
        )


def downgrade() -> None:
    """Drop leaves table."""
    op.drop_table("leaves")
