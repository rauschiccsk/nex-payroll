"""Employee API router — CRUD endpoints.

Prefix: /api/v1/employees (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
Soft-delete via is_deleted flag — list excludes deleted records by default.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services import employee as employee_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Employees"])


@router.get("", response_model=PaginatedResponse[EmployeeRead])
def list_employees_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    include_deleted: bool = Query(  # noqa: B008
        False, description="Include soft-deleted records"
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of employees."""
    items = employee_service.list_employees(
        db,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
    )
    total = employee_service.count_employees(
        db,
        tenant_id=tenant_id,
        include_deleted=include_deleted,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee_endpoint(
    employee_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single employee by ID."""
    employee = employee_service.get_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee_endpoint(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new employee."""
    try:
        employee = employee_service.create_employee(db, payload)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "invalid" in msg or "constraint" in msg:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee_endpoint(
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing employee."""
    try:
        employee = employee_service.update_employee(db, employee_id, payload)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if "invalid" in msg or "constraint" in msg:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=204)
def delete_employee_endpoint(
    employee_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete an employee by ID."""
    deleted = employee_service.delete_employee(db, employee_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.commit()
