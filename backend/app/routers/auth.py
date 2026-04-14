"""Auth API router — OAuth2 login and current-user endpoints.

DESIGN.md §6.1:
  POST /api/v1/auth/login   — OAuth2 password flow → JWT access token
  GET  /api/v1/auth/me      — current user info (requires valid token)

Prefix /api/v1/auth is set in main.py.
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.schemas.user import UserRead
from app.services.user_service import authenticate_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])


# ---------------------------------------------------------------------------
# Schemas (auth-specific)
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Authenticate user via username + password and return JWT access token.

    Username format: plain ``username`` (tenant resolved from X-Tenant header
    or first active user with that username across tenants in Phase I).
    Returns HTTP 401 on invalid credentials or inactive account.
    """
    user = authenticate_user(db, form_data.username, form_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserRead)
def get_me(
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> User:
    """Return the currently authenticated user's profile.

    Requires valid Bearer token in Authorization header.
    Returns HTTP 401 if token is missing, invalid, or expired.
    """
    return current_user
