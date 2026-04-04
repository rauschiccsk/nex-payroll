"""ContributionRate model — versioned contribution/levy rates.

Schema: shared
Stores SP/ZP contribution rates with validity periods.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, CheckConstraint, Date, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class ContributionRate(Base):
    """Versioned contribution rates for social/health insurance funds.

    Lives in the 'shared' schema — shared across all tenants.
    Only created_at (no updated_at) — rates are immutable once created.
    """

    __tablename__ = "contribution_rates"
    __table_args__ = (
        Index("ix_contribution_rates_rate_type_valid_from", "rate_type", "valid_from"),
        CheckConstraint(
            "payer IN ('employee', 'employer')",
            name="ck_contribution_rates_payer",
        ),
        {"schema": "shared"},
    )

    # PK — UUIDMixin inline (shared schema model)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    rate_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="e.g. sp_employee_nemocenske, zp_employee",
    )

    rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(6, 4),
        nullable=False,
    )

    max_assessment_base: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    payer: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="employee or employer",
    )

    fund: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Only created_at — rates are immutable
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<ContributionRate(rate_type={self.rate_type!r}, "
            f"payer={self.payer!r}, rate={self.rate_percent}%, "
            f"valid_from={self.valid_from})>"
        )
