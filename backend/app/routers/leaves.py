"""Leave API router — CRUD endpoints.

Prefix: /api/v1/leaves (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.leave import LeaveCreate, LeaveRead, LeaveUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.leave import (
    count_leaves,
    create_leave,
    delete_leave,
    get_leave,
    list_leaves,
    update_leave,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Leaves"])


@router.get("", response_model=PaginatedResponse[LeaveRead])
def list_leaves_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    status: str | None = Query(None, description="Filter by status (pending, approved, rejected, cancelled)"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of leave records."""
    items = list_leaves(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        status=status,
        skip=skip,
        limit=limit,
    )
    total = count_leaves(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        status=status,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{leave_id}", response_model=LeaveRead)
def get_leave_endpoint(
    leave_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single leave record by ID."""
    leave = get_leave(db, leave_id)
    if leave is None:
        raise HTTPException(status_code=404, detail="Leave not found")
    return leave


@router.post("", response_model=LeaveRead, status_code=201)
def create_leave_endpoint(
    payload: LeaveCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new leave record."""
    leave = create_leave(db, payload)
    db.commit()
    db.refresh(leave)
    return leave


@router.put("/{leave_id}", response_model=LeaveRead)
def update_leave_endpoint(
    leave_id: UUID,
    payload: LeaveUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing leave record."""
    try:
        leave = update_leave(db, leave_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(leave)
    return leave


@router.delete("/{leave_id}", status_code=204)
def delete_leave_endpoint(
    leave_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a leave record by ID."""
    try:
        deleted = delete_leave(db, leave_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Leave not found")
    db.commit()
