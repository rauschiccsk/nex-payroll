"""Create monthly_reports table.

Revision ID: 011
Revises: 010
Create Date: 2026-04-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: str | Sequence[str] | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create monthly_reports table with constraints and indexes."""
    op.create_table(
        "monthly_reports",
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
            "health_insurer_id",
            sa.UUID(),
            nullable=True,
            comment="Reference to health insurer (for ZP report types)",
        ),
        sa.Column(
            "period_year",
            sa.Integer(),
            nullable=False,
            comment="Report period — calendar year",
        ),
        sa.Column(
            "period_month",
            sa.Integer(),
            nullable=False,
            comment="Report period — calendar month (1-12)",
        ),
        sa.Column(
            "report_type",
            sa.String(length=30),
            nullable=False,
            comment="Report type: sp_monthly, zp_vszp, zp_dovera, zp_union, tax_prehled",
        ),
        sa.Column(
            "file_path",
            sa.String(length=500),
            nullable=False,
            comment="Path to generated report file",
        ),
        sa.Column(
            "file_format",
            sa.String(length=10),
            nullable=False,
            server_default="xml",
            comment="File format of the report (default: xml)",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="generated",
            comment="Report status: generated, submitted, accepted, rejected",
        ),
        sa.Column(
            "deadline_date",
            sa.Date(),
            nullable=False,
            comment="Statutory deadline date for submission",
        ),
        sa.Column(
            "institution",
            sa.String(length=100),
            nullable=False,
            comment="Target institution (e.g. Sociálna poisťovňa, VšZP)",
        ),
        sa.Column(
            "submitted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Timestamp when the report was submitted",
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
            "report_type IN ('sp_monthly', 'zp_vszp', 'zp_dovera', "
            "'zp_union', 'tax_prehled')",
            name="ck_monthly_reports_report_type",
        ),
        sa.CheckConstraint(
            "status IN ('generated', 'submitted', 'accepted', 'rejected')",
            name="ck_monthly_reports_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenants.id"],
            name="fk_monthly_reports_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["health_insurer_id"],
            ["shared.health_insurers.id"],
            name="fk_monthly_reports_health_insurer_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "period_year",
            "period_month",
            "report_type",
            name="uq_monthly_reports_tenant_year_month_type",
        ),
    )

    with op.batch_alter_table("monthly_reports") as batch_op:
        batch_op.create_index(
            "ix_monthly_reports_tenant_period",
            ["tenant_id", "period_year", "period_month"],
            unique=False,
        )


def downgrade() -> None:
    """Drop monthly_reports table."""
    op.drop_table("monthly_reports")
