"""Notification model — user notifications for deadlines, anomalies, approvals.

Schema: tenant-specific
Tracks notifications for users including deadline reminders,
AI-detected payroll anomalies, approval requests, and system errors.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Notification(UUIDMixin, TimestampMixin, Base):
    """User notification record.

    Tenant-specific table — lives in the tenant's dedicated schema.
    Each record represents a single notification for one user,
    with a type, severity, and read/unread status.

    Note: TimestampMixin provides created_at and updated_at.
    The DESIGN.md spec shows only created_at for this entity,
    but we keep updated_at from the mixin for consistency across all models.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('deadline', 'anomaly', 'system', 'approval')",
            name="ck_notifications_type",
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_notifications_severity",
        ),
        Index(
            "ix_notifications_tenant_user_is_read",
            "tenant_id",
            "user_id",
            "is_read",
        ),
        Index(
            "ix_notifications_tenant_created_at",
            "tenant_id",
            text("created_at DESC"),
        ),
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        comment="Reference to owning tenant",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        comment="Reference to target user",
    )

    # -- Notification content --

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Notification type: deadline, anomaly, system, approval",
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="info",
        comment="Severity level: info, warning, critical",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Short notification title",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full notification message body",
    )

    # -- Related entity (polymorphic reference) --

    related_entity: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Entity type name this notification relates to (e.g. 'payroll', 'leave')",
    )

    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the related entity",
    )

    # -- Read tracking --

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="Whether user has read this notification",
    )

    read_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when user read the notification",
    )

    def __repr__(self) -> str:
        return (
            f"<Notification(user_id={self.user_id!r}, "
            f"type={self.type!r}, "
            f"severity={self.severity!r}, "
            f"title={self.title!r}, "
            f"is_read={self.is_read!r})>"
        )
