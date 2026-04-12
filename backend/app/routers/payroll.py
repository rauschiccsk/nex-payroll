"""Payroll API router — CRUD endpoints.

Prefix: /api/v1/payroll (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.payroll import PayrollCreate, PayrollRead, PayrollUpdate
from app.services import payroll as payroll_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payroll"])


# ---------------------------------------------------------------------------
# Error-mapping helper (DRY — shared across create/update/delete)
# ---------------------------------------------------------------------------


def _raise_for_value_error(exc: ValueError) -> None:
    """Map *ValueError* message to the appropriate HTTP status code.

    Pattern:
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
# GET  /payroll                        — paginated list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[PayrollRead])
def list_payrolls_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    status: str | None = Query(None, description="Filter by status (draft, calculated, approved, paid)"),  # noqa: B008
    period_year: int | None = Query(None, ge=2000, le=2100, description="Filter by period year"),  # noqa: B008
    period_month: int | None = Query(None, ge=1, le=12, description="Filter by period month (1-12)"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of payroll records."""
    try:
        items = payroll_service.list_payrolls(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            status=status,
            period_year=period_year,
            period_month=period_month,
            skip=skip,
            limit=limit,
        )
        total = payroll_service.count_payrolls(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            status=status,
            period_year=period_year,
            period_month=period_month,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /payroll/{payroll_id}           — detail
# ---------------------------------------------------------------------------


@router.get("/{payroll_id}", response_model=PayrollRead)
def get_payroll_endpoint(
    payroll_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single payroll record by ID."""
    payroll = payroll_service.get_payroll(db, payroll_id)
    if payroll is None:
        raise HTTPException(status_code=404, detail="Payroll not found")
    return payroll


# ---------------------------------------------------------------------------
# POST /payroll                        — create
# ---------------------------------------------------------------------------


@router.post("", response_model=PayrollRead, status_code=201)
def create_payroll_endpoint(
    payload: PayrollCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new payroll record."""
    try:
        payroll = payroll_service.create_payroll(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(payroll)
    return payroll


# ---------------------------------------------------------------------------
# PATCH /payroll/{payroll_id}          — partial update
# ---------------------------------------------------------------------------


@router.patch("/{payroll_id}", response_model=PayrollRead)
def update_payroll_endpoint(
    payroll_id: UUID,
    payload: PayrollUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing payroll record (partial — only supplied fields change)."""
    try:
        payroll = payroll_service.update_payroll(db, payroll_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(payroll)
    return payroll


# ---------------------------------------------------------------------------
# DELETE /payroll/{payroll_id}         — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{payroll_id}", status_code=204)
def delete_payroll_endpoint(
    payroll_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a payroll record by ID."""
    try:
        payroll_service.delete_payroll(db, payroll_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
