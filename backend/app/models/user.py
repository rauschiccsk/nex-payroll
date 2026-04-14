"""User model — system user with authentication and RBAC.

Schema: public (multi-tenant with tenant_id FK)
Represents a user who can log into the system. Linked to a tenant
and optionally to an employee record.
Password is hashed using Argon2 via pwdlib.
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    """System user with authentication and role-based access control.

    Lives in the public schema. Uses tenant_id FK for tenant isolation.
    Roles: superadmin, director, accountant, employee.
    Business rules:
      - role='superadmin' MUST have tenant_id=NULL
      - role!='superadmin' MUST have tenant_id set
      - role='employee' MUST have employee_id set
      - role='director'|'accountant' MAY have employee_id
      - Soft delete via is_active=False
      - password_hash uses Argon2 via pwdlib
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "username",
            name="uq_users_tenant_username",
        ),
        UniqueConstraint(
            "tenant_id",
            "email",
            name="uq_users_tenant_email",
        ),
        Index(
            "uq_users_employee_id",
            "employee_id",
            unique=True,
            postgresql_where="employee_id IS NOT NULL",
        ),
        CheckConstraint(
            "role IN ('superadmin', 'director', 'accountant', 'employee')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "(role = 'superadmin' AND tenant_id IS NULL) OR (role != 'superadmin' AND tenant_id IS NOT NULL)",
            name="ck_users_superadmin_no_tenant",
        ),
        Index("ix_users_tenant_role", "tenant_id", "role"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        {"extend_existing": True},
    )

    # -- Relationships / foreign keys --

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Reference to owning tenant (NULL for superadmin)",
    )

    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Optional link to employee record (required for role='employee')",
    )

    # -- Authentication --

    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Login username (unique within tenant)",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email address (unique within tenant)",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Argon2 password hash via pwdlib",
    )

    # -- RBAC --

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="User role: superadmin, director, accountant, employee",
    )

    # -- Status --

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Soft-delete flag (False = deactivated user)",
    )

    # -- Tracking --

    last_login_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp of last successful login",
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp of last password change",
    )

    def __repr__(self) -> str:
        return f"<User(username={self.username!r}, role={self.role!r}, is_active={self.is_active!r})>"
