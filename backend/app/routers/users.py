"""User API router — CRUD endpoints.

Prefix: /api/v1/users (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.user import (
    count_users,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserRead])
def list_users_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    role: str | None = Query(None, description="Filter by role"),  # noqa: B008
    include_inactive: bool = Query(False, description="Include inactive users"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of users."""
    items = list_users(
        db,
        tenant_id=tenant_id,
        role=role,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
    )
    total = count_users(
        db,
        tenant_id=tenant_id,
        role=role,
        include_inactive=include_inactive,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(
    user_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single user by ID."""
    user = get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("", response_model=UserRead, status_code=201)
def create_user_endpoint(
    payload: UserCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new user."""
    try:
        user = create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user_endpoint(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing user."""
    try:
        user = update_user(db, user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user_endpoint(
    user_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a user by ID."""
    deleted = delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    db.commit()
