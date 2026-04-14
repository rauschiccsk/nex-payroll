"""Pydantic v2 schemas for User entity.

Used for API request validation (Create/Update) and response serialisation (Read).
Provides UserBase, UserCreate, UserUpdate, UserInDB (full DB read),
and UserPublic (safe subset for API responses).

password_hash is write-only — it appears in UserInDB but NEVER in public responses.
"""

import re
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Reusable type aliases
# ---------------------------------------------------------------------------

_ROLE = Literal["director", "accountant", "employee"]

# ---------------------------------------------------------------------------
# Validation constants & patterns
# ---------------------------------------------------------------------------

_PASSWORD_MIN_LENGTH = 12
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _strip_not_blank(value: str, field_name: str) -> str:
    """Strip whitespace and ensure not blank."""
    stripped = value.strip()
    if not stripped:
        msg = f"{field_name} must not be blank"
        raise ValueError(msg)
    return stripped


def _validate_email_format(value: str) -> str:
    """Validate e-mail address format."""
    cleaned = value.strip().lower()
    if not _EMAIL_RE.match(cleaned):
        msg = "Invalid email format"
        raise ValueError(msg)
    return cleaned


def _validate_password_complexity(value: str) -> str:
    """Validate password complexity: uppercase, lowercase, digit, special char."""
    if not re.search(r"[A-Z]", value):
        msg = "Password must contain at least one uppercase letter"
        raise ValueError(msg)
    if not re.search(r"[a-z]", value):
        msg = "Password must contain at least one lowercase letter"
        raise ValueError(msg)
    if not re.search(r"\d", value):
        msg = "Password must contain at least one digit"
        raise ValueError(msg)
    if not re.search(r"[^a-zA-Z0-9]", value):
        msg = "Password must contain at least one special character"
        raise ValueError(msg)
    return value


# ---------------------------------------------------------------------------
# UserBase — shared writable fields
# ---------------------------------------------------------------------------


class UserBase(BaseModel):
    """Common fields shared between Create and Read schemas."""

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
    def _email_format(cls, v: str) -> str:
        return _validate_email_format(v)


# ---------------------------------------------------------------------------
# UserCreate
# ---------------------------------------------------------------------------


class UserCreate(UserBase):
    """Schema for creating a new user.

    Inherits username, email, role, is_active from UserBase.
    Adds password (plaintext, hashed server-side) and tenant_id.
    """

    password: str = Field(
        ...,
        min_length=_PASSWORD_MIN_LENGTH,
        max_length=255,
        description="Plaintext password — hashed server-side via pwdlib (Argon2)",
    )
    tenant_id: UUID = Field(
        ...,
        description="Reference to owning tenant (public.tenants.id). Required — NOT NULL in DB.",
    )
    employee_id: UUID | None = Field(
        default=None,
        description="Optional link to employee record (required for role='employee')",
    )

    @field_validator("password")
    @classmethod
    def _password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)

    @model_validator(mode="after")
    def _role_constraints(self) -> Self:
        """Business rules:
        - employee → employee_id is required
        """
        if self.role == "employee" and self.employee_id is None:
            raise ValueError("employee_id is required when role is 'employee'")
        return self


# ---------------------------------------------------------------------------
# UserUpdate — all fields Optional
# ---------------------------------------------------------------------------


class UserUpdate(BaseModel):
    """Schema for updating a user.

    All fields optional — only supplied fields are updated.
    Immutable fields (id, created_at, tenant_id) are excluded.
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
    def _email_format(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_email_format(v)
        return v

    @field_validator("password")
    @classmethod
    def _password_complexity(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_password_complexity(v)
        return v


# ---------------------------------------------------------------------------
# UserInDB — full representation from database (all columns)
# ---------------------------------------------------------------------------


class UserInDB(UserBase):
    """Full user representation as stored in the database.

    Includes all model columns (PK, FKs, password_hash, timestamps).
    Not intended for API responses — use UserRead or UserPublic instead.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID | None = None
    password_hash: str
    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# UserRead — API response (excludes password_hash)
# ---------------------------------------------------------------------------


class UserRead(BaseModel):
    """Schema for returning a user in API responses.

    Note: password_hash is intentionally excluded for security.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    employee_id: UUID | None = None
    username: str
    email: str
    role: _ROLE
    is_active: bool
    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# UserPublic — safe subset for API responses
# ---------------------------------------------------------------------------


class UserPublic(BaseModel):
    """Safe subset of user data exposed in public-facing API responses.

    Omits sensitive fields like password_hash, employee_id, timestamps.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    role: _ROLE
    is_active: bool
    tenant_id: UUID
    last_login_at: datetime | None = None
