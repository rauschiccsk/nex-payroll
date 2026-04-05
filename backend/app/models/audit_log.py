"""AuditLog model — immutable audit trail.

Schema: public
Records every CREATE, UPDATE, DELETE action across the system.
Audit entries are immutable — no updated_at column.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class AuditLog(UUIDMixin, Base):
    """Immutable audit record for entity changes.

    Lives in the 'public' schema.
    Each record captures who did what, when, and the before/after state.
    No updated_at — audit entries are never modified.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(
            "action IN ('CREATE', 'UPDATE', 'DELETE')",
            name="ck_audit_log_action",
        ),
        Index(
            "ix_audit_log_tenant_entity",
            "tenant_id",
            "entity_type",
            "entity_id",
        ),
        Index(
            "ix_audit_log_tenant_created",
            "tenant_id",
            "created_at",
            postgresql_using="btree",
        ),
        {"schema": "public"},
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        comment="Reference to tenant (public.tenants.id)",
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who performed the action (NULL for system actions)",
    )

    action: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Action type: CREATE, UPDATE, DELETE",
    )

    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Fully qualified entity/table name",
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Primary key of the affected entity",
    )

    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Entity state before the change (NULL for CREATE)",
    )

    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Entity state after the change (NULL for DELETE)",
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (IPv4 or IPv6)",
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the audit record was created",
    )

    def __repr__(self) -> str:
        return f"<AuditLog(action={self.action!r}, entity_type={self.entity_type!r}, entity_id={self.entity_id!r})>"
