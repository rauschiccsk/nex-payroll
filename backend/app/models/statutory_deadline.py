"""StatutoryDeadline model — statutory reporting deadlines.

Schema: shared
Stores statutory deadlines for SP/ZP/tax reporting (zákonné termíny).
"""

from datetime import date, datetime

from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, Date, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class StatutoryDeadline(UUIDMixin, Base):
    """Statutory reporting deadline definition.

    Lives in the 'shared' schema — shared across all tenants.
    Only created_at (no updated_at) — reference data, immutable once created.

    Defines recurring deadlines for:
      - SP monthly report (Mesačný výkaz SP)
      - ZP monthly report (Mesačný výkaz ZP)
      - Tax advance payment (Preddavok na daň)
      - Tax reconciliation (Ročné zúčtovanie)
    """

    __tablename__ = "statutory_deadlines"
    __table_args__ = (
        Index("ix_statutory_deadlines_deadline_type", "deadline_type"),
        Index("ix_statutory_deadlines_valid_from", "valid_from"),
        CheckConstraint(
            "deadline_type IN ("
            "'sp_monthly', 'zp_monthly', 'tax_advance', "
            "'tax_reconciliation', 'sp_annual', 'zp_annual')",
            name="ck_statutory_deadlines_deadline_type",
        ),
        {"schema": "shared"},
    )

    deadline_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Type: sp_monthly, zp_monthly, tax_advance, tax_reconciliation, sp_annual, zp_annual",
    )

    institution: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Target institution (e.g. Sociálna poisťovňa, VšZP, DÚ)",
    )

    day_of_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Day of month the deadline falls on",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable description (Slovak)",
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    # Only created_at — reference data, immutable
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<StatutoryDeadline(type={self.deadline_type!r}, "
            f"institution={self.institution!r}, "
            f"day={self.day_of_month}, "
            f"valid_from={self.valid_from})>"
        )
