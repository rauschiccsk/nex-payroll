"""PaySlip API router — CRUD endpoints.

Prefix: /api/v1/payslips (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.pay_slip import PaySlipCreate, PaySlipRead, PaySlipUpdate
from app.services.pay_slip import (
    count_pay_slips,
    create_pay_slip,
    delete_pay_slip,
    get_pay_slip,
    list_pay_slips,
    update_pay_slip,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pay Slips"])


@router.get("", response_model=PaginatedResponse[PaySlipRead])
def list_pay_slips_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    payroll_id: UUID | None = Query(None, description="Filter by payroll"),  # noqa: B008
    period_year: int | None = Query(None, description="Filter by period year"),  # noqa: B008
    period_month: int | None = Query(  # noqa: B008
        None, ge=1, le=12, description="Filter by period month (1-12)"
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of pay slip records."""
    items = list_pay_slips(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        payroll_id=payroll_id,
        period_year=period_year,
        period_month=period_month,
        skip=skip,
        limit=limit,
    )
    total = count_pay_slips(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        payroll_id=payroll_id,
        period_year=period_year,
        period_month=period_month,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{pay_slip_id}", response_model=PaySlipRead)
def get_pay_slip_endpoint(
    pay_slip_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single pay slip record by ID."""
    pay_slip = get_pay_slip(db, pay_slip_id)
    if pay_slip is None:
        raise HTTPException(status_code=404, detail="Pay slip not found")
    return pay_slip


@router.post("", response_model=PaySlipRead, status_code=201)
def create_pay_slip_endpoint(
    payload: PaySlipCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new pay slip record."""
    try:
        pay_slip = create_pay_slip(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(pay_slip)
    return pay_slip


@router.put("/{pay_slip_id}", response_model=PaySlipRead)
def update_pay_slip_endpoint(
    pay_slip_id: UUID,
    payload: PaySlipUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing pay slip record."""
    try:
        pay_slip = update_pay_slip(db, pay_slip_id, payload)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    db.commit()
    db.refresh(pay_slip)
    return pay_slip


@router.delete("/{pay_slip_id}", status_code=204)
def delete_pay_slip_endpoint(
    pay_slip_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a pay slip record by ID."""
    try:
        delete_pay_slip(db, pay_slip_id)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    db.commit()
