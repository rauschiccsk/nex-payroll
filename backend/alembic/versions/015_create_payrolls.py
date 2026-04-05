"""Create payrolls table.

Revision ID: 015
Revises: 014
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: str | Sequence[str] | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create payrolls table with constraints and indexes."""
    op.create_table(
        "payrolls",
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
            "employee_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to employee",
        ),
        sa.Column(
            "contract_id",
            sa.UUID(),
            nullable=False,
            comment="Reference to active contract used for this payroll",
        ),
        # -- Period --
        sa.Column(
            "period_year",
            sa.Integer(),
            nullable=False,
            comment="Payroll period year (e.g. 2025)",
        ),
        sa.Column(
            "period_month",
            sa.Integer(),
            nullable=False,
            comment="Payroll period month (1-12)",
        ),
        # -- Status --
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
            comment="Payroll status: draft, calculated, approved, paid",
        ),
        # -- Gross wage components --
        sa.Column(
            "base_wage",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Base wage from contract",
        ),
        sa.Column(
            "overtime_hours",
            sa.Numeric(precision=6, scale=2),
            nullable=False,
            server_default="0",
            comment="Number of overtime hours worked",
        ),
        sa.Column(
            "overtime_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
            comment="Overtime pay amount",
        ),
        sa.Column(
            "bonus_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
            comment="Bonus amount for the period",
        ),
        sa.Column(
            "supplement_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
            comment="Supplementary pay (night, weekend, holiday)",
        ),
        sa.Column(
            "gross_wage",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Total gross wage (base + overtime + bonus + supplement)",
        ),
        # -- SP employee contributions --
        sa.Column(
            "sp_assessment_base",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Social insurance assessment base",
        ),
        sa.Column(
            "sp_nemocenske",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employee sickness insurance contribution",
        ),
        sa.Column(
            "sp_starobne",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employee old-age pension contribution",
        ),
        sa.Column(
            "sp_invalidne",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employee disability insurance contribution",
        ),
        sa.Column(
            "sp_nezamestnanost",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employee unemployment insurance contribution",
        ),
        sa.Column(
            "sp_employee_total",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Total employee social insurance contributions",
        ),
        # -- ZP employee contribution --
        sa.Column(
            "zp_assessment_base",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Health insurance assessment base",
        ),
        sa.Column(
            "zp_employee",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employee health insurance contribution",
        ),
        # -- Tax calculation --
        sa.Column(
            "partial_tax_base",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Partial tax base (gross - SP employee - ZP employee)",
        ),
        sa.Column(
            "nczd_applied",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Non-taxable amount (NCZD) applied",
        ),
        sa.Column(
            "tax_base",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Final tax base after NCZD deduction",
        ),
        sa.Column(
            "tax_advance",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Advance income tax amount",
        ),
        sa.Column(
            "child_bonus",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
            comment="Child tax bonus (danovy bonus na deti)",
        ),
        sa.Column(
            "tax_after_bonus",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Tax after child bonus deduction",
        ),
        # -- Net wage --
        sa.Column(
            "net_wage",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Net wage paid to employee",
        ),
        # -- SP employer contributions --
        sa.Column(
            "sp_employer_nemocenske",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer sickness insurance contribution",
        ),
        sa.Column(
            "sp_employer_starobne",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer old-age pension contribution",
        ),
        sa.Column(
            "sp_employer_invalidne",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer disability insurance contribution",
        ),
        sa.Column(
            "sp_employer_nezamestnanost",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer unemployment insurance contribution",
        ),
        sa.Column(
            "sp_employer_garancne",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer guarantee fund contribution",
        ),
        sa.Column(
            "sp_employer_rezervny",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer reserve fund contribution",
        ),
        sa.Column(
            "sp_employer_kurzarbeit",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer short-time work (kurzarbeit) contribution",
        ),
        sa.Column(
            "sp_employer_urazove",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer accident insurance contribution",
        ),
        sa.Column(
            "sp_employer_total",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Total employer social insurance contributions",
        ),
        sa.Column(
            "zp_employer",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Employer health insurance contribution",
        ),
        sa.Column(
            "total_employer_cost",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            comment="Total employer cost (gross + SP employer + ZP employer)",
        ),
        # -- Pillar 2 --
        sa.Column(
            "pillar2_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
            comment="II. pillar pension saving deduction",
        ),
        # -- AI validation --
        sa.Column(
            "ai_validation_result",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="AI validation result (anomalies, confidence score)",
        ),
        # -- Ledger sync --
        sa.Column(
            "ledger_sync_status",
            sa.String(length=20),
            nullable=True,
            comment="Ledger synchronization status: pending, synced, error",
        ),
        # -- Approval metadata --
        sa.Column(
            "calculated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when payroll was calculated",
        ),
        sa.Column(
            "approved_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when payroll was approved",
        ),
        sa.Column(
            "approved_by",
            sa.UUID(),
            nullable=True,
            comment="User who approved the payroll",
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
            "status IN ('draft', 'calculated', 'approved', 'paid')",
            name="ck_payrolls_status",
        ),
        sa.CheckConstraint(
            "ledger_sync_status IN ('pending', 'synced', 'error')",
            name="ck_payrolls_ledger_sync_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_payrolls_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.id"],
            name="fk_payrolls_employee_id",
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name="fk_payrolls_contract_id",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_payrolls_approved_by",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "employee_id",
            "period_year",
            "period_month",
            name="uq_payrolls_tenant_employee_period",
        ),
    )

    with op.batch_alter_table("payrolls") as batch_op:
        batch_op.create_index(
            "ix_payrolls_tenant_period_status",
            ["tenant_id", "period_year", "period_month", "status"],
            unique=False,
        )


def downgrade() -> None:
    """Drop payrolls table."""
    op.drop_table("payrolls")
