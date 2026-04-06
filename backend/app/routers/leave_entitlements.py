"""LeaveEntitlement API router — CRUD endpoints.

Prefix: /api/v1/leave-entitlements (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.leave_entitlement import (
    LeaveEntitlementCreate,
    LeaveEntitlementRead,
    LeaveEntitlementUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services.leave_entitlement import (
    count_leave_entitlements,
    create_leave_entitlement,
    delete_leave_entitlement,
    get_leave_entitlement,
    list_leave_entitlements,
    update_leave_entitlement,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Leave Entitlements"])


@router.get("", response_model=PaginatedResponse[LeaveEntitlementRead])
def list_leave_entitlements_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    year: int | None = Query(None, ge=2000, le=2100, description="Filter by calendar year"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of leave entitlements."""
    items = list_leave_entitlements(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        year=year,
        skip=skip,
        limit=limit,
    )
    total = count_leave_entitlements(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        year=year,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{entitlement_id}", response_model=LeaveEntitlementRead)
def get_leave_entitlement_endpoint(
    entitlement_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single leave entitlement by ID."""
    entitlement = get_leave_entitlement(db, entitlement_id)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="Leave entitlement not found")
    return entitlement


@router.post("", response_model=LeaveEntitlementRead, status_code=201)
def create_leave_entitlement_endpoint(
    payload: LeaveEntitlementCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new leave entitlement record."""
    try:
        entitlement = create_leave_entitlement(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(entitlement)
    return entitlement


@router.put("/{entitlement_id}", response_model=LeaveEntitlementRead)
def update_leave_entitlement_endpoint(
    entitlement_id: UUID,
    payload: LeaveEntitlementUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing leave entitlement record."""
    try:
        entitlement = update_leave_entitlement(db, entitlement_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(entitlement)
    return entitlement


@router.delete("/{entitlement_id}", status_code=204)
def delete_leave_entitlement_endpoint(
    entitlement_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a leave entitlement by ID."""
    try:
        deleted = delete_leave_entitlement(db, entitlement_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Leave entitlement not found")
    db.commit()
