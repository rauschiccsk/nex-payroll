"""add_journal_entries

Revision ID: 022
Revises: 021
Create Date: 2026-04-13 17:17:36.569886

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "022"
down_revision: str | None = "021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("public.tenants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "payroll_id",
            sa.UUID(),
            sa.ForeignKey("payrolls.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "period_year",
            sa.Integer(),
            nullable=False,
            comment="Accounting period year",
        ),
        sa.Column(
            "period_month",
            sa.Integer(),
            nullable=False,
            comment="Accounting period month (1-12)",
        ),
        sa.Column(
            "entry_date",
            sa.Date(),
            nullable=False,
            comment="Journal entry date (last day of period)",
        ),
        sa.Column(
            "account_code",
            sa.String(length=10),
            nullable=False,
            comment="Slovak chart of accounts code",
        ),
        sa.Column(
            "account_name",
            sa.String(length=100),
            nullable=False,
            comment="Account name for display",
        ),
        sa.Column(
            "entry_type",
            sa.String(length=6),
            nullable=False,
            comment="Entry type: debit or credit",
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            comment="Entry amount (always positive)",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            comment="Entry description / narration",
        ),
        sa.Column(
            "sync_batch_id",
            sa.String(length=50),
            nullable=True,
            comment="Batch ID for sync grouping",
        ),
        sa.Column(
            "synced_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When synced to NEX Ledger",
        ),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
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
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "entry_type IN ('debit', 'credit')",
            name="ck_journal_entries_entry_type",
        ),
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_journal_entries_amount_positive",
        ),
    )
    with op.batch_alter_table("journal_entries", schema=None) as batch_op:
        batch_op.create_index(
            "ix_journal_entries_payroll_id",
            ["payroll_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_journal_entries_tenant_period",
            ["tenant_id", "period_year", "period_month"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("journal_entries", schema=None) as batch_op:
        batch_op.drop_index("ix_journal_entries_tenant_period")
        batch_op.drop_index("ix_journal_entries_payroll_id")

    op.drop_table("journal_entries")
