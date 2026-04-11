"""Pydantic v2 schemas for User entity.

Used for API request validation (Create/Update) and response serialisation (Read).
password_hash is write-only — it appears in Create but NEVER in Read responses.
"""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_ROLE = Literal["director", "accountant", "employee"]

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

# Password: minimum 8 characters
_PASSWORD_MIN_LENGTH = 8


def _strip_not_blank(value: str, field_name: str) -> str:
    """Strip whitespace and ensure not blank."""
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} must not be blank"
        raise ValueError(msg)
    return stripped


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
        min_length=1,
        max_length=100,
        examples=["jnovak"],
        description="Login username (unique within tenant)",
    )
    email: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["jan.novak@example.com"],
        description="Email address (unique within tenant)",
    )
    password: str = Field(
        ...,
        min_length=_PASSWORD_MIN_LENGTH,
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

    @field_validator("username")
    @classmethod
    def _username_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "Username")

    @field_validator("email")
    @classmethod
    def _email_not_blank(cls, v: str) -> str:
        return _strip_not_blank(v, "Email")

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
    username: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(
        default=None,
        min_length=_PASSWORD_MIN_LENGTH,
        max_length=255,
        description="New plaintext password — hashed server-side via pwdlib (Argon2)",
    )
    role: _ROLE | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @field_validator("username")
    @classmethod
    def _username_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "Username")
        return v

    @field_validator("email")
    @classmethod
    def _email_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            return _strip_not_blank(v, "Email")
        return v


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
