"""Nested employee-children routes under /employees/{employee_id}/children.

DESIGN.md §6.6 — employee children are sub-resources of employees.
Prefix /api/v1 is set in main.py; this router adds
/employees/{employee_id}/children.

All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.employee_child import EmployeeChildCreate, EmployeeChildRead
from app.schemas.pagination import PaginatedResponse
from app.services import employee_child as employee_child_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/employees/{employee_id}/children",
    tags=["Employee Children"],
)


@router.get("", response_model=PaginatedResponse[EmployeeChildRead])
def list_children_by_employee(
    employee_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedResponse[EmployeeChildRead]:
    """Return paginated children for a specific employee."""
    items = employee_child_service.list_employee_children(db, employee_id=employee_id, skip=skip, limit=limit)
    total = employee_child_service.count_employee_children(db, employee_id=employee_id)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=EmployeeChildRead, status_code=201)
def create_child_for_employee(
    employee_id: UUID,
    data: EmployeeChildCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> EmployeeChildRead:
    """Create a new child record for the given employee.

    The employee_id path param overrides any employee_id in the request body.
    """
    payload_data = data.model_dump()
    payload_data["employee_id"] = employee_id
    merged = EmployeeChildCreate(**payload_data)

    try:
        child = employee_child_service.create_employee_child(db, merged)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if any(kw in msg for kw in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(child)
    return child
