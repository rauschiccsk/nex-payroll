"""Pydantic v2 schemas for Notification entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Each record represents a single notification for one user,
with a type, severity, and read/unread status.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_NOTIFICATION_TYPE = Literal["deadline", "anomaly", "system", "approval"]

_NOTIFICATION_SEVERITY = Literal["info", "warning", "critical"]


# ---------------------------------------------------------------------------
# NotificationCreate
# ---------------------------------------------------------------------------


class NotificationCreate(BaseModel):
    """Schema for creating a new notification."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    user_id: UUID = Field(
        ...,
        description="Reference to target user (users.id)",
    )
    type: _NOTIFICATION_TYPE = Field(
        ...,
        max_length=50,
        examples=["deadline"],
        description=("Notification type: deadline, anomaly, system, approval"),
    )
    severity: _NOTIFICATION_SEVERITY = Field(
        default="info",
        max_length=20,
        examples=["info"],
        description="Severity level: info, warning, critical",
    )
    title: str = Field(
        ...,
        max_length=200,
        examples=["Blíži sa termín pre výkaz SP"],
        description="Short notification title",
    )
    message: str = Field(
        ...,
        examples=["Termín pre mesačný výkaz SP je o 3 dni."],
        description="Full notification message body",
    )
    related_entity: str | None = Field(
        default=None,
        max_length=50,
        examples=["payroll"],
        description=("Entity type name this notification relates to (e.g. 'payroll', 'leave')"),
    )
    related_entity_id: UUID | None = Field(
        default=None,
        description="ID of the related entity",
    )

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        """Title must not be empty or whitespace-only."""
        stripped = v.strip()
        if not stripped:
            msg = "title must not be empty or whitespace-only"
            raise ValueError(msg)
        return stripped

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, v: str) -> str:
        """Message body must not be empty or whitespace-only."""
        stripped = v.strip()
        if not stripped:
            msg = "message must not be empty or whitespace-only"
            raise ValueError(msg)
        return stripped


# ---------------------------------------------------------------------------
# NotificationUpdate
# ---------------------------------------------------------------------------


class NotificationUpdate(BaseModel):
    """Schema for updating a notification.

    All fields optional — only supplied fields are updated.
    """

    type: _NOTIFICATION_TYPE | None = Field(
        default=None,
        max_length=50,
        description="Notification type: deadline, anomaly, system, approval",
    )
    severity: _NOTIFICATION_SEVERITY | None = Field(
        default=None,
        max_length=20,
        description="Severity level: info, warning, critical",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Short notification title",
    )
    message: str | None = Field(
        default=None,
        description="Full notification message body",
    )
    related_entity: str | None = Field(
        default=None,
        max_length=50,
        description="Entity type name this notification relates to",
    )
    related_entity_id: UUID | None = Field(
        default=None,
        description="ID of the related entity",
    )
    is_read: bool | None = Field(
        default=None,
        description="Whether user has read this notification",
    )
    read_at: datetime | None = Field(
        default=None,
        description="Timestamp when user read the notification",
    )

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str | None) -> str | None:
        """When supplied, title must not be empty or whitespace-only."""
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            msg = "title must not be empty or whitespace-only"
            raise ValueError(msg)
        return stripped

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, v: str | None) -> str | None:
        """When supplied, message must not be empty or whitespace-only."""
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            msg = "message must not be empty or whitespace-only"
            raise ValueError(msg)
        return stripped


# ---------------------------------------------------------------------------
# NotificationRead
# ---------------------------------------------------------------------------


class NotificationRead(BaseModel):
    """Schema for returning a notification in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID
    type: _NOTIFICATION_TYPE
    severity: _NOTIFICATION_SEVERITY
    title: str
    message: str
    related_entity: str | None
    related_entity_id: UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime
