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
from app.services import leave_entitlement as leave_entitlement_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Leave Entitlements"])


# ---------------------------------------------------------------------------
# Error-mapping helper (DRY — shared across create/update/delete)
# ---------------------------------------------------------------------------


def _raise_for_value_error(exc: ValueError) -> None:
    """Map *ValueError* message to the appropriate HTTP status code.

    Pattern (per Router Generation Checklist):
      "not found"                          -> 404
      "duplicate" / "conflict" / "already exists" -> 409
      "invalid" / "constraint" / "foreign key"    -> 422
      anything else                        -> 409 (business-rule violation)
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
# GET  /leave-entitlements          — paginated list
# ---------------------------------------------------------------------------


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
    items = leave_entitlement_service.list_leave_entitlements(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        year=year,
        skip=skip,
        limit=limit,
    )
    total = leave_entitlement_service.count_leave_entitlements(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        year=year,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /leave-entitlements/{id}     — detail
# ---------------------------------------------------------------------------


@router.get("/{entitlement_id}", response_model=LeaveEntitlementRead)
def get_leave_entitlement_endpoint(
    entitlement_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single leave entitlement by ID."""
    entitlement = leave_entitlement_service.get_leave_entitlement(db, entitlement_id)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="Leave entitlement not found")
    return entitlement


# ---------------------------------------------------------------------------
# POST /leave-entitlements          — create
# ---------------------------------------------------------------------------


@router.post("", response_model=LeaveEntitlementRead, status_code=201)
def create_leave_entitlement_endpoint(
    payload: LeaveEntitlementCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new leave entitlement record."""
    try:
        entitlement = leave_entitlement_service.create_leave_entitlement(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(entitlement)
    return entitlement


# ---------------------------------------------------------------------------
# PATCH /leave-entitlements/{id}    — partial update
# ---------------------------------------------------------------------------


@router.patch("/{entitlement_id}", response_model=LeaveEntitlementRead)
def update_leave_entitlement_endpoint(
    entitlement_id: UUID,
    payload: LeaveEntitlementUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing leave entitlement record (partial — only supplied fields change)."""
    try:
        entitlement = leave_entitlement_service.update_leave_entitlement(db, entitlement_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(entitlement)
    return entitlement


# ---------------------------------------------------------------------------
# DELETE /leave-entitlements/{id}   — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{entitlement_id}", status_code=204)
def delete_leave_entitlement_endpoint(
    entitlement_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a leave entitlement by ID."""
    try:
        deleted = leave_entitlement_service.delete_leave_entitlement(db, entitlement_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail="Leave entitlement not found")
    db.commit()
