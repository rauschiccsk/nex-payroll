"""Sync all models — FK ondelete RESTRICT, audit_log index fix.

Revision ID: 019
Revises: 018
Create Date: 2026-04-11 00:00:00.000000

Brings DB in line with all model definitions:
- Add ondelete='RESTRICT' to foreign keys where models require it
- Fix audit_log index to use DESC on created_at
Note: statutory_deadlines was already created correctly in migration 004.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: str | Sequence[str] | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Helper: replace a FK constraint with new delete rule
# ---------------------------------------------------------------------------
def _replace_fk(
    table: str,
    constraint_name: str,
    local_col: str,
    ref_table: str,
    ref_col: str = "id",
    ondelete: str = "RESTRICT",
    ref_schema: str | None = None,
) -> None:
    """Drop old FK and create new one with the specified ondelete rule."""
    op.drop_constraint(constraint_name, table, type_="foreignkey")
    op.create_foreign_key(
        constraint_name,
        table,
        ref_table,
        [local_col],
        [ref_col],
        ondelete=ondelete,
        referent_schema=ref_schema,
    )


def upgrade() -> None:
    """Upgrade schema."""
    # -----------------------------------------------------------------------
    # 1. FK ondelete='RESTRICT' updates
    # -----------------------------------------------------------------------

    # contracts
    _replace_fk("contracts", "fk_contracts_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="RESTRICT")
    _replace_fk("contracts", "fk_contracts_employee_id", "employee_id", "employees", ondelete="RESTRICT")

    # employee_children — tenant_id only (employee_id already RESTRICT from 009)
    _replace_fk(
        "employee_children",
        "fk_employee_children_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="RESTRICT",
    )

    # leave_entitlements — tenant_id only (employee_id already RESTRICT from 010)
    _replace_fk(
        "leave_entitlements",
        "fk_leave_entitlements_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="RESTRICT",
    )

    # leaves
    _replace_fk("leaves", "fk_leaves_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="RESTRICT")
    _replace_fk("leaves", "fk_leaves_employee_id", "employee_id", "employees", ondelete="RESTRICT")
    _replace_fk("leaves", "fk_leaves_approved_by", "approved_by", "users", ondelete="RESTRICT")

    # monthly_reports
    _replace_fk(
        "monthly_reports",
        "fk_monthly_reports_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="RESTRICT",
    )
    _replace_fk(
        "monthly_reports",
        "fk_monthly_reports_health_insurer_id",
        "health_insurer_id",
        "health_insurers",
        ref_schema="shared",
        ondelete="RESTRICT",
    )

    # notifications
    _replace_fk(
        "notifications", "fk_notifications_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="RESTRICT"
    )
    _replace_fk("notifications", "fk_notifications_user_id", "user_id", "users", ondelete="RESTRICT")

    # pay_slips
    _replace_fk("pay_slips", "fk_pay_slips_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="RESTRICT")
    _replace_fk("pay_slips", "fk_pay_slips_employee_id", "employee_id", "employees", ondelete="RESTRICT")
    _replace_fk("pay_slips", "fk_pay_slips_payroll_id", "payroll_id", "payrolls", ondelete="RESTRICT")

    # payment_orders
    _replace_fk(
        "payment_orders",
        "fk_payment_orders_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="RESTRICT",
    )
    _replace_fk("payment_orders", "fk_payment_orders_employee_id", "employee_id", "employees", ondelete="RESTRICT")
    _replace_fk(
        "payment_orders",
        "fk_payment_orders_health_insurer_id",
        "health_insurer_id",
        "health_insurers",
        ref_schema="shared",
        ondelete="RESTRICT",
    )

    # payrolls
    _replace_fk("payrolls", "fk_payrolls_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="RESTRICT")
    _replace_fk("payrolls", "fk_payrolls_employee_id", "employee_id", "employees", ondelete="RESTRICT")
    _replace_fk("payrolls", "fk_payrolls_contract_id", "contract_id", "contracts", ondelete="RESTRICT")
    _replace_fk("payrolls", "fk_payrolls_approved_by", "approved_by", "users", ondelete="RESTRICT")

    # users
    _replace_fk("users", "fk_users_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="RESTRICT")
    _replace_fk("users", "fk_users_employee_id", "employee_id", "employees", ondelete="RESTRICT")

    # -----------------------------------------------------------------------
    # 2. audit_log — fix index to DESC on created_at
    # -----------------------------------------------------------------------
    op.drop_index("ix_audit_log_tenant_created", table_name="audit_log", schema="public")
    op.execute(sa.text("CREATE INDEX ix_audit_log_tenant_created ON public.audit_log (tenant_id, created_at DESC)"))


def downgrade() -> None:
    """Downgrade schema."""
    # -----------------------------------------------------------------------
    # 2. audit_log — revert index
    # -----------------------------------------------------------------------
    op.drop_index("ix_audit_log_tenant_created", table_name="audit_log", schema="public")
    op.create_index(
        "ix_audit_log_tenant_created",
        "audit_log",
        ["tenant_id", "created_at"],
        schema="public",
    )

    # -----------------------------------------------------------------------
    # 1. FK — revert to NO ACTION
    # -----------------------------------------------------------------------
    # users
    _replace_fk("users", "fk_users_employee_id", "employee_id", "employees", ondelete="NO ACTION")
    _replace_fk("users", "fk_users_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="NO ACTION")

    # payrolls
    _replace_fk("payrolls", "fk_payrolls_approved_by", "approved_by", "users", ondelete="NO ACTION")
    _replace_fk("payrolls", "fk_payrolls_contract_id", "contract_id", "contracts", ondelete="NO ACTION")
    _replace_fk("payrolls", "fk_payrolls_employee_id", "employee_id", "employees", ondelete="NO ACTION")
    _replace_fk("payrolls", "fk_payrolls_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="NO ACTION")

    # payment_orders
    _replace_fk(
        "payment_orders",
        "fk_payment_orders_health_insurer_id",
        "health_insurer_id",
        "health_insurers",
        ref_schema="shared",
        ondelete="NO ACTION",
    )
    _replace_fk("payment_orders", "fk_payment_orders_employee_id", "employee_id", "employees", ondelete="NO ACTION")
    _replace_fk(
        "payment_orders",
        "fk_payment_orders_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="NO ACTION",
    )

    # pay_slips
    _replace_fk("pay_slips", "fk_pay_slips_payroll_id", "payroll_id", "payrolls", ondelete="NO ACTION")
    _replace_fk("pay_slips", "fk_pay_slips_employee_id", "employee_id", "employees", ondelete="NO ACTION")
    _replace_fk(
        "pay_slips", "fk_pay_slips_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="NO ACTION"
    )

    # notifications
    _replace_fk("notifications", "fk_notifications_user_id", "user_id", "users", ondelete="NO ACTION")
    _replace_fk(
        "notifications", "fk_notifications_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="NO ACTION"
    )

    # monthly_reports
    _replace_fk(
        "monthly_reports",
        "fk_monthly_reports_health_insurer_id",
        "health_insurer_id",
        "health_insurers",
        ref_schema="shared",
        ondelete="NO ACTION",
    )
    _replace_fk(
        "monthly_reports",
        "fk_monthly_reports_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="NO ACTION",
    )

    # leaves
    _replace_fk("leaves", "fk_leaves_approved_by", "approved_by", "users", ondelete="NO ACTION")
    _replace_fk("leaves", "fk_leaves_employee_id", "employee_id", "employees", ondelete="NO ACTION")
    _replace_fk("leaves", "fk_leaves_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="NO ACTION")

    # leave_entitlements
    _replace_fk(
        "leave_entitlements",
        "fk_leave_entitlements_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="NO ACTION",
    )

    # employee_children
    _replace_fk(
        "employee_children",
        "fk_employee_children_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="NO ACTION",
    )

    # contracts
    _replace_fk("contracts", "fk_contracts_employee_id", "employee_id", "employees", ondelete="NO ACTION")
    _replace_fk(
        "contracts", "fk_contracts_tenant_id", "tenant_id", "tenants", ref_schema="public", ondelete="NO ACTION"
    )
