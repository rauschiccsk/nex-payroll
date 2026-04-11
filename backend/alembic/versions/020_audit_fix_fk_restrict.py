"""Add ondelete=RESTRICT to audit_log and employees FKs.

Revision ID: 020
Revises: 019
Create Date: 2026-04-11 00:00:00.000000

Phase 1 audit fix: audit_log.tenant_id, employees.tenant_id,
and employees.health_insurer_id were missing ondelete='RESTRICT'.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: str | Sequence[str] | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_fk(
    table: str,
    constraint_name: str,
    local_col: str,
    ref_table: str,
    ref_col: str = "id",
    ondelete: str = "RESTRICT",
    ref_schema: str | None = None,
    source_schema: str | None = None,
) -> None:
    """Drop old FK and create new one with the specified ondelete rule."""
    op.drop_constraint(constraint_name, table, type_="foreignkey", schema=source_schema)
    op.create_foreign_key(
        constraint_name,
        table,
        ref_table,
        [local_col],
        [ref_col],
        ondelete=ondelete,
        referent_schema=ref_schema,
        source_schema=source_schema,
    )


def upgrade() -> None:
    """Add RESTRICT to audit_log and employees FKs."""
    # audit_log.tenant_id -> public.tenants.id
    _replace_fk(
        "audit_log",
        "fk_audit_log_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        source_schema="public",
        ondelete="RESTRICT",
    )

    # employees.tenant_id -> public.tenants.id
    _replace_fk(
        "employees",
        "fk_employees_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="RESTRICT",
    )

    # employees.health_insurer_id -> shared.health_insurers.id
    _replace_fk(
        "employees",
        "fk_employees_health_insurer_id",
        "health_insurer_id",
        "health_insurers",
        ref_schema="shared",
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Revert to NO ACTION."""
    _replace_fk(
        "employees",
        "fk_employees_health_insurer_id",
        "health_insurer_id",
        "health_insurers",
        ref_schema="shared",
        ondelete="NO ACTION",
    )

    _replace_fk(
        "employees",
        "fk_employees_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        ondelete="NO ACTION",
    )

    _replace_fk(
        "audit_log",
        "fk_audit_log_tenant_id",
        "tenant_id",
        "tenants",
        ref_schema="public",
        source_schema="public",
        ondelete="NO ACTION",
    )
