"""StatutoryDeadline API router — CRUD endpoints.

Prefix: /api/v1/statutory-deadlines (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.statutory_deadline import (
    StatutoryDeadlineCreate,
    StatutoryDeadlineRead,
    StatutoryDeadlineUpdate,
)
from app.services.statutory_deadline import (
    count_statutory_deadlines,
    create_statutory_deadline,
    delete_statutory_deadline,
    get_statutory_deadline,
    list_statutory_deadlines,
    update_statutory_deadline,
)

router = APIRouter(tags=["Statutory Deadlines"])


@router.get("", response_model=PaginatedResponse[StatutoryDeadlineRead])
def list_deadlines(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of statutory deadlines."""
    items = list_statutory_deadlines(db, skip=skip, limit=limit)
    total = count_statutory_deadlines(db)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{deadline_id}", response_model=StatutoryDeadlineRead)
def get_deadline(
    deadline_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single statutory deadline by ID."""
    deadline = get_statutory_deadline(db, deadline_id)
    if deadline is None:
        raise HTTPException(status_code=404, detail="Statutory deadline not found")
    return deadline


@router.post("", response_model=StatutoryDeadlineRead, status_code=201)
def create_deadline(
    payload: StatutoryDeadlineCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new statutory deadline."""
    deadline = create_statutory_deadline(db, payload)
    db.commit()
    db.refresh(deadline)
    return deadline


@router.patch("/{deadline_id}", response_model=StatutoryDeadlineRead)
def update_deadline(
    deadline_id: UUID,
    payload: StatutoryDeadlineUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing statutory deadline."""
    deadline = update_statutory_deadline(db, deadline_id, payload)
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
    deleted = delete_statutory_deadline(db, deadline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Statutory deadline not found")
    db.commit()
