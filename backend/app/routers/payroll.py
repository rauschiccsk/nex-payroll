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
from app.services.payroll import (
    count_payrolls,
    create_payroll,
    delete_payroll,
    get_payroll,
    list_payrolls,
    update_payroll,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payroll"])


@router.get("", response_model=PaginatedResponse[PayrollRead])
def list_payrolls_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    status: str | None = Query(None, description="Filter by status (draft, calculated, approved, paid)"),  # noqa: B008
    period_year: int | None = Query(None, description="Filter by period year"),  # noqa: B008
    period_month: int | None = Query(None, ge=1, le=12, description="Filter by period month (1-12)"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of payroll records."""
    items = list_payrolls(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        status=status,
        period_year=period_year,
        period_month=period_month,
        skip=skip,
        limit=limit,
    )
    total = count_payrolls(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        status=status,
        period_year=period_year,
        period_month=period_month,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{payroll_id}", response_model=PayrollRead)
def get_payroll_endpoint(
    payroll_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single payroll record by ID."""
    payroll = get_payroll(db, payroll_id)
    if payroll is None:
        raise HTTPException(status_code=404, detail="Payroll not found")
    return payroll


@router.post("", response_model=PayrollRead, status_code=201)
def create_payroll_endpoint(
    payload: PayrollCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new payroll record."""
    try:
        payroll = create_payroll(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(payroll)
    return payroll


@router.put("/{payroll_id}", response_model=PayrollRead)
def update_payroll_endpoint(
    payroll_id: UUID,
    payload: PayrollUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing payroll record."""
    try:
        payroll = update_payroll(db, payroll_id, payload)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    db.commit()
    db.refresh(payroll)
    return payroll


@router.delete("/{payroll_id}", status_code=204)
def delete_payroll_endpoint(
    payroll_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a payroll record by ID."""
    try:
        delete_payroll(db, payroll_id)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    db.commit()
