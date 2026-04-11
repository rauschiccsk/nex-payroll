"""StatutoryDeadline model — statutory reporting deadlines.

Schema: shared
Stores statutory deadlines for SP/ZP/tax reporting (zákonné termíny).
"""

from datetime import date, datetime

from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, Date, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class StatutoryDeadline(UUIDMixin, Base):
    """Statutory reporting deadline definition.

    Lives in the 'shared' schema — shared across all tenants.
    Only created_at (no updated_at) — reference data, immutable once created.

    Defines recurring deadlines for:
      - SP monthly report (Mesačný výkaz SP)
      - ZP monthly report (Mesačný prehľad ZP)
      - Tax advance payment (Preddavok dane)
      - Tax reconciliation (Hlásenie o dani ročné)
      - Annual certificates and reports
    """

    __tablename__ = "statutory_deadlines"
    __table_args__ = (
        Index("ix_statutory_deadlines_deadline_type", "deadline_type"),
        Index("ix_statutory_deadlines_valid_from", "valid_from"),
        CheckConstraint(
            "deadline_type IN ('monthly', 'annual', 'one_time')",
            name="ck_statutory_deadlines_deadline_type",
        ),
        UniqueConstraint("code", name="uq_statutory_deadlines_code"),
        {"schema": "shared"},
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unique code identifier (e.g. SP_MONTHLY, ZP_MONTHLY)",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional longer description (Slovak)",
    )

    deadline_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type: monthly, annual, one_time",
    )

    day_of_month: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Day of month the deadline falls on (NULL if not applicable)",
    )

    month_of_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Month of year for annual deadlines (1-12, NULL for monthly)",
    )

    business_days_rule: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="If true, deadline shifts to next business day",
    )

    institution: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Target institution (e.g. Sociálna poisťovňa, VšZP, DÚ)",
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Only created_at — reference data, immutable
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<StatutoryDeadline(code={self.code!r}, "
            f"type={self.deadline_type!r}, "
            f"institution={self.institution!r}, "
            f"day={self.day_of_month}, "
            f"valid_from={self.valid_from})>"
        )
