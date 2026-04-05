"""Create employee_children table.

Revision ID: 009
Revises: 008
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | Sequence[str] | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create employee_children table with constraints and indexes."""
    op.create_table(
        "employee_children",
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
            comment="Reference to parent employee",
        ),
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
            comment="Child first name",
        ),
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=False,
            comment="Child last name",
        ),
        sa.Column(
            "birth_date",
            sa.Date(),
            nullable=False,
            comment="Child date of birth",
        ),
        sa.Column(
            "birth_number",
            sa.Text(),
            nullable=True,
            comment="Child birth number (rodné číslo) — encrypted at rest",
        ),
        sa.Column(
            "is_tax_bonus_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether the child is eligible for daňový bonus",
        ),
        sa.Column(
            "custody_from",
            sa.Date(),
            nullable=True,
            comment="Start of custody period (NULL = since birth)",
        ),
        sa.Column(
            "custody_to",
            sa.Date(),
            nullable=True,
            comment="End of custody period (NULL = ongoing)",
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
            name="fk_employee_children_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_employee_children_employee_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("employee_children") as batch_op:
        batch_op.create_index(
            "ix_employee_children_tenant_employee",
            ["tenant_id", "employee_id"],
            unique=False,
        )


def downgrade() -> None:
    """Drop employee_children table."""
    op.drop_table("employee_children")
