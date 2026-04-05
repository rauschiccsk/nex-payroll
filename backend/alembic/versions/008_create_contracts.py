"""Create contracts table.

Revision ID: 008
Revises: 007
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | Sequence[str] | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create contracts table with constraints and indexes."""
    op.create_table(
        "contracts",
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
            "contract_number",
            sa.String(length=50),
            nullable=False,
            comment="Unique contract number within tenant",
        ),
        sa.Column(
            "contract_type",
            sa.String(length=30),
            nullable=False,
            comment="Contract type: permanent, fixed_term, agreement_work, agreement_activity",
        ),
        sa.Column(
            "job_title",
            sa.String(length=200),
            nullable=False,
            comment="Job position title",
        ),
        sa.Column(
            "wage_type",
            sa.String(length=20),
            nullable=False,
            comment="Wage type: monthly or hourly",
        ),
        sa.Column(
            "base_wage",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Base wage amount (monthly or hourly rate)",
        ),
        sa.Column(
            "hours_per_week",
            sa.Numeric(precision=4, scale=1),
            nullable=False,
            server_default="40.0",
            comment="Contracted weekly working hours",
        ),
        sa.Column(
            "start_date",
            sa.Date(),
            nullable=False,
            comment="Contract start date",
        ),
        sa.Column(
            "end_date",
            sa.Date(),
            nullable=True,
            comment="Contract end date (NULL for indefinite contracts)",
        ),
        sa.Column(
            "probation_end_date",
            sa.Date(),
            nullable=True,
            comment="End date of probation period",
        ),
        sa.Column(
            "termination_date",
            sa.Date(),
            nullable=True,
            comment="Actual termination date (NULL if not terminated)",
        ),
        sa.Column(
            "termination_reason",
            sa.String(length=200),
            nullable=True,
            comment="Reason for contract termination",
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether this is the currently active contract",
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
            "contract_type IN ('permanent', 'fixed_term', 'agreement_work', 'agreement_activity')",
            name="ck_contracts_contract_type",
        ),
        sa.CheckConstraint(
            "wage_type IN ('monthly', 'hourly')",
            name="ck_contracts_wage_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_contracts_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_contracts_employee_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "contract_number",
            name="uq_contracts_tenant_contract_number",
        ),
    )

    with op.batch_alter_table("contracts") as batch_op:
        batch_op.create_index(
            "ix_contracts_tenant_employee_current",
            ["tenant_id", "employee_id", "is_current"],
            unique=False,
        )


def downgrade() -> None:
    """Drop contracts table."""
    op.drop_table("contracts")
