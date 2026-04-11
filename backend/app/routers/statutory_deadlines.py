"""StatutoryDeadline API router — CRUD endpoints.

Prefix: /api/v1/statutory-deadlines (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.statutory_deadline import (
    StatutoryDeadlineCreate,
    StatutoryDeadlineRead,
    StatutoryDeadlineUpdate,
)
from app.services import statutory_deadline as statutory_deadline_service

router = APIRouter(tags=["Statutory Deadlines"])


@router.get("", response_model=PaginatedResponse[StatutoryDeadlineRead])
def list_deadlines(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of statutory deadlines."""
    items = statutory_deadline_service.list_statutory_deadlines(db, skip=skip, limit=limit)
    total = statutory_deadline_service.count_statutory_deadlines(db)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{deadline_id}", response_model=StatutoryDeadlineRead)
def get_deadline(
    deadline_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single statutory deadline by ID."""
    deadline = statutory_deadline_service.get_statutory_deadline(db, deadline_id)
    if deadline is None:
        raise HTTPException(status_code=404, detail="Statutory deadline not found")
    return deadline


@router.post("", response_model=StatutoryDeadlineRead, status_code=201)
def create_deadline(
    payload: StatutoryDeadlineCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new statutory deadline."""
    try:
        deadline = statutory_deadline_service.create_statutory_deadline(db, payload)
        db.commit()
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Statutory deadline with code '{payload.code}' already exists",
        ) from None
    db.refresh(deadline)
    return deadline


@router.patch("/{deadline_id}", response_model=StatutoryDeadlineRead)
def update_deadline(
    deadline_id: UUID,
    payload: StatutoryDeadlineUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing statutory deadline."""
    try:
        deadline = statutory_deadline_service.update_statutory_deadline(db, deadline_id, payload)
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Statutory deadline with this code already exists",
        ) from None
    if deadline is None:
        raise HTTPException(status_code=404, detail="Statutory deadline not found")
    db.commit()
    db.refresh(deadline)
    return deadline


@router.delete("/{deadline_id}", status_code=204)
def delete_deadline(
    deadline_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a statutory deadline by ID."""
    deleted = statutory_deadline_service.delete_statutory_deadline(db, deadline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Statutory deadline not found")
    db.commit()
