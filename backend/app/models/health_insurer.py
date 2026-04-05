"""HealthInsurer model — Slovak health insurance companies.

Schema: shared
Reference/seed data for health insurers (VšZP, Dôvera, Union).
"""

from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class HealthInsurer(UUIDMixin, Base):
    """Health insurance company reference record.

    Lives in the 'shared' schema — shared across all tenants.
    Only created_at (no updated_at) — reference data, rarely changed.

    Seed data:
      24 — Dôvera zdravotná poisťovňa, a.s.
      25 — Všeobecná zdravotná poisťovňa, a.s. (VšZP)
      27 — Union zdravotná poisťovňa, a.s.
    """

    __tablename__ = "health_insurers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_health_insurers_code"),
        {"schema": "shared"},
    )

    code: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
        comment="Insurer code (e.g. 24, 25, 27)",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    iban: Mapped[str] = mapped_column(
        String(34),
        nullable=False,
    )

    bic: Mapped[str | None] = mapped_column(
        String(11),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    # Only created_at — reference data
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<HealthInsurer(code={self.code!r}, "
            f"name={self.name!r}, "
            f"is_active={self.is_active})>"
        )
