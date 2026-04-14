"""Pydantic v2 schemas for authentication (JWT, Login, Password)."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import _PASSWORD_MIN_LENGTH, UserPublic, _validate_password_complexity


class TokenPayload(BaseModel):
    """JWT token payload (decoded claims)."""

    sub: UUID  # user_id
    tenant_id: UUID | None = None
    role: str
    exp: int


class Token(BaseModel):
    """OAuth2-compatible token response."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Credentials for user login."""

    username: str
    password: str


class LoginResponse(Token):
    """Token response enriched with user profile."""

    user: UserPublic


class ChangePasswordRequest(BaseModel):
    """Request to change user password with complexity validation."""

    old_password: str
    new_password: str = Field(..., min_length=_PASSWORD_MIN_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Enforce minimum password complexity.

        Delegates to the shared _validate_password_complexity helper from
        app.schemas.user to keep password policy consistent across the app.
        """
        return _validate_password_complexity(v)
