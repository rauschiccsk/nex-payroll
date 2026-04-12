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
from app.services import employee_child as employee_child_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Employee Children"])


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
# GET  /employee-children          — paginated list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[EmployeeChildRead])
def list_employee_children_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of employee children."""
    items = employee_child_service.list_employee_children(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        skip=skip,
        limit=limit,
    )
    total = employee_child_service.count_employee_children(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /employee-children/{id}     — detail
# ---------------------------------------------------------------------------


@router.get("/{child_id}", response_model=EmployeeChildRead)
def get_employee_child_endpoint(
    child_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single employee child by ID."""
    child = employee_child_service.get_employee_child(db, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Employee child not found")
    return child


# ---------------------------------------------------------------------------
# POST /employee-children          — create
# ---------------------------------------------------------------------------


@router.post("", response_model=EmployeeChildRead, status_code=201)
def create_employee_child_endpoint(
    payload: EmployeeChildCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new employee child record."""
    try:
        child = employee_child_service.create_employee_child(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(child)
    return child


# ---------------------------------------------------------------------------
# PATCH /employee-children/{id}    — partial update
# ---------------------------------------------------------------------------


@router.patch("/{child_id}", response_model=EmployeeChildRead)
def update_employee_child_endpoint(
    child_id: UUID,
    payload: EmployeeChildUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing employee child record (partial — only supplied fields change)."""
    try:
        child = employee_child_service.update_employee_child(db, child_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    if child is None:
        raise HTTPException(status_code=404, detail="Employee child not found")
    db.commit()
    db.refresh(child)
    return child


# ---------------------------------------------------------------------------
# DELETE /employee-children/{id}   — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{child_id}", status_code=204)
def delete_employee_child_endpoint(
    child_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete an employee child by ID."""
    try:
        deleted = employee_child_service.delete_employee_child(db, child_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail="Employee child not found")
    db.commit()
