"""EmployeeChild API router — CRUD endpoints.

Prefix: /api/v1/employee-children (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.employee_child import (
    EmployeeChildCreate,
    EmployeeChildRead,
    EmployeeChildUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services.employee_child import (
    count_employee_children,
    create_employee_child,
    delete_employee_child,
    get_employee_child,
    list_employee_children,
    update_employee_child,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Employee Children"])


@router.get("", response_model=PaginatedResponse[EmployeeChildRead])
def list_employee_children_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of employee children."""
    items = list_employee_children(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        skip=skip,
        limit=limit,
    )
    total = count_employee_children(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{child_id}", response_model=EmployeeChildRead)
def get_employee_child_endpoint(
    child_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single employee child by ID."""
    child = get_employee_child(db, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Employee child not found")
    return child


@router.post("", response_model=EmployeeChildRead, status_code=201)
def create_employee_child_endpoint(
    payload: EmployeeChildCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new employee child record."""
    try:
        child = create_employee_child(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(child)
    return child


@router.put("/{child_id}", response_model=EmployeeChildRead)
def update_employee_child_endpoint(
    child_id: UUID,
    payload: EmployeeChildUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing employee child record."""
    try:
        child = update_employee_child(db, child_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if child is None:
        raise HTTPException(status_code=404, detail="Employee child not found")
    db.commit()
    db.refresh(child)
    return child


@router.delete("/{child_id}", status_code=204)
def delete_employee_child_endpoint(
    child_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete an employee child by ID."""
    try:
        deleted = delete_employee_child(db, child_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Employee child not found")
    db.commit()
