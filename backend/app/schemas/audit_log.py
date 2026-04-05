"""Pydantic v2 schemas for AuditLog entity.

Used for API request validation (Create/Update) and response serialisation (Read).
AuditLog entries are immutable — Update schema exists for consistency but all
fields are optional (practical use is limited since audit records should not be
modified).
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogCreate(BaseModel):
    """Schema for creating a new audit log entry."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to tenant (public.tenants.id)",
    )
    user_id: UUID | None = Field(
        default=None,
        description="User who performed the action (NULL for system actions)",
    )
    action: Literal["CREATE", "UPDATE", "DELETE"] = Field(
        ...,
        examples=["CREATE"],
        description="Action type: CREATE, UPDATE, DELETE",
    )
    entity_type: str = Field(
        ...,
        max_length=100,
        examples=["employees"],
        description="Fully qualified entity/table name",
    )
    entity_id: UUID = Field(
        ...,
        description="Primary key of the affected entity",
    )
    old_values: dict[str, Any] | None = Field(
        default=None,
        description="Entity state before the change (NULL for CREATE)",
    )
    new_values: dict[str, Any] | None = Field(
        default=None,
        description="Entity state after the change (NULL for DELETE)",
    )
    ip_address: str | None = Field(
        default=None,
        max_length=45,
        examples=["192.168.1.1"],
        description="Client IP address (IPv4 or IPv6)",
    )


class AuditLogUpdate(BaseModel):
    """Schema for updating an audit log entry.

    All fields optional — only supplied fields are updated.
    Note: audit log entries are immutable by design; this schema exists
    for API consistency.
    """

    tenant_id: UUID | None = Field(
        default=None,
    )
    user_id: UUID | None = Field(
        default=None,
    )
    action: Literal["CREATE", "UPDATE", "DELETE"] | None = Field(
        default=None,
    )
    entity_type: str | None = Field(
        default=None,
        max_length=100,
    )
    entity_id: UUID | None = Field(
        default=None,
    )
    old_values: dict[str, Any] | None = Field(
        default=None,
    )
    new_values: dict[str, Any] | None = Field(
        default=None,
    )
    ip_address: str | None = Field(
        default=None,
        max_length=45,
    )


class AuditLogRead(BaseModel):
    """Schema for returning an audit log entry in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID
    old_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime
