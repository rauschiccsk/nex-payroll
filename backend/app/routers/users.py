"""User API router — CRUD endpoints.

Prefix: /api/v1/users (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import ROLE_ACCOUNTANT, ROLE_DIRECTOR
from app.models.user import User as UserModel
from app.schemas.pagination import PaginatedResponse
from app.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services import user as user_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])


# ---------------------------------------------------------------------------
# Error-mapping helper (DRY — shared across create/update/delete)
# ---------------------------------------------------------------------------


def _raise_for_value_error(exc: ValueError) -> None:
    """Map *ValueError* message to the appropriate HTTP status code.

    Pattern (per Router Generation Checklist):
      "not found"                          → 404
      "duplicate" / "conflict" / "already exists" → 409
      "invalid" / "constraint" / "foreign key"    → 422
      anything else                        → 409 (business-rule violation)
    """
    msg = str(exc).lower()
    if "not found" in msg:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if any(kw in msg for kw in ("duplicate", "conflict", "already exists")):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if any(kw in msg for kw in ("invalid", "constraint", "foreign key")):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Fallback — treat as conflict (dependency / business-rule violation)
    raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET list — paginated
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[UserRead])
def list_users_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    role: str | None = Query(None, description="Filter by role"),  # noqa: B008
    include_inactive: bool = Query(False, description="Include inactive users"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    current_user: UserModel = Depends(require_role(ROLE_DIRECTOR, ROLE_ACCOUNTANT)),  # noqa: B008
):
    """Return a paginated list of users."""
    items = user_service.list_users(
        db,
        tenant_id=tenant_id,
        role=role,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
    )
    total = user_service.count_users(
        db,
        tenant_id=tenant_id,
        role=role,
        include_inactive=include_inactive,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(
    user_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: UserModel = Depends(require_role(ROLE_DIRECTOR, ROLE_ACCOUNTANT)),  # noqa: B008
):
    """Return a single user by ID."""
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# POST — create
# ---------------------------------------------------------------------------


@router.post("", response_model=UserRead, status_code=201)
def create_user_endpoint(
    payload: UserCreate,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: UserModel = Depends(require_role(ROLE_DIRECTOR)),  # noqa: B008
):
    """Create a new user."""
    try:
        user = user_service.create_user(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# PATCH — partial update
# ---------------------------------------------------------------------------


@router.patch("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: UserModel = Depends(require_role(ROLE_DIRECTOR)),  # noqa: B008
):
    """Update an existing user (partial)."""
    try:
        user = user_service.update_user(db, user_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# DELETE — soft-delete
# ---------------------------------------------------------------------------


@router.delete("/{user_id}", status_code=204)
def delete_user_endpoint(
    user_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: UserModel = Depends(require_role(ROLE_DIRECTOR)),  # noqa: B008
):
    """Soft-delete a user by setting is_active=False."""
    deleted = user_service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
