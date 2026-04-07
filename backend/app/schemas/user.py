"""Pydantic v2 schemas for User entity.

Used for API request validation (Create/Update) and response serialisation (Read).
password_hash is write-only — it appears in Create but NEVER in Read responses.
"""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_ROLE = Literal["director", "accountant", "employee"]


# ---------------------------------------------------------------------------
# UserCreate
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id)",
    )
    employee_id: UUID | None = Field(
        default=None,
        description="Optional link to employee record (required for role='employee')",
    )
    username: str = Field(
        ...,
        max_length=100,
        examples=["jnovak"],
        description="Login username (unique within tenant)",
    )
    email: str = Field(
        ...,
        max_length=255,
        examples=["jan.novak@example.com"],
        description="Email address (unique within tenant)",
    )
    password: str = Field(
        ...,
        max_length=255,
        description="Plaintext password — hashed server-side via pwdlib (Argon2)",
    )
    role: _ROLE = Field(
        ...,
        examples=["accountant"],
        description="User role: director, accountant, employee",
    )
    is_active: bool = Field(
        default=True,
        description="Whether user account is active",
    )

    @model_validator(mode="after")
    def employee_role_requires_employee_id(self) -> Self:
        """Business rule: role='employee' MUST have employee_id set."""
        if self.role == "employee" and self.employee_id is None:
            raise ValueError("employee_id is required when role is 'employee'")
        return self


# ---------------------------------------------------------------------------
# UserUpdate
# ---------------------------------------------------------------------------


class UserUpdate(BaseModel):
    """Schema for updating a user.

    All fields optional — only supplied fields are updated.
    """

    employee_id: UUID | None = Field(default=None)
    username: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    password: str | None = Field(
        default=None,
        max_length=255,
        description="New plaintext password — hashed server-side via pwdlib (Argon2)",
    )
    role: _ROLE | None = Field(default=None)
    is_active: bool | None = Field(default=None)


# ---------------------------------------------------------------------------
# UserRead
# ---------------------------------------------------------------------------


class UserRead(BaseModel):
    """Schema for returning a user in API responses.

    Note: password_hash is intentionally excluded for security.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID | None
    username: str
    email: str
    role: _ROLE
    is_active: bool
    last_login_at: datetime | None
    password_changed_at: datetime | None
    created_at: datetime
    updated_at: datetime
