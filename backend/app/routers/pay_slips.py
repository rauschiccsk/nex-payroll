"""PaySlip API router — CRUD + PDF generation endpoints.

Prefix: /api/v1/payslips (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.

Endpoints per DESIGN.md §6.8:
  GET    /payslips/{year}/{month}/{employee_id}/pdf   — Download PDF
  POST   /payslips/{year}/{month}/generate-all        — Batch generate all
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.pay_slip import (
    PaySlipCreate,
    PaySlipGenerateAllResponse,
    PaySlipRead,
    PaySlipUpdate,
)
from app.services import pay_slip as pay_slip_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pay Slips"])


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
# GET  /payslips                        — paginated list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[PaySlipRead])
def list_pay_slips_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    payroll_id: UUID | None = Query(None, description="Filter by payroll"),  # noqa: B008
    period_year: int | None = Query(  # noqa: B008
        None, ge=2000, le=2100, description="Filter by period year"
    ),
    period_month: int | None = Query(  # noqa: B008
        None, ge=1, le=12, description="Filter by period month (1-12)"
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of pay slip records."""
    items = pay_slip_service.list_pay_slips(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        payroll_id=payroll_id,
        period_year=period_year,
        period_month=period_month,
        skip=skip,
        limit=limit,
    )
    total = pay_slip_service.count_pay_slips(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        payroll_id=payroll_id,
        period_year=period_year,
        period_month=period_month,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /payslips/{pay_slip_id}          — detail
# ---------------------------------------------------------------------------


@router.get("/{pay_slip_id}", response_model=PaySlipRead)
def get_pay_slip_endpoint(
    pay_slip_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single pay slip record by ID."""
    pay_slip = pay_slip_service.get_pay_slip(db, pay_slip_id)
    if pay_slip is None:
        raise HTTPException(status_code=404, detail="Pay slip not found")
    return pay_slip


# ---------------------------------------------------------------------------
# POST /payslips                        — create
# ---------------------------------------------------------------------------


@router.post("", response_model=PaySlipRead, status_code=201)
def create_pay_slip_endpoint(
    payload: PaySlipCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new pay slip record."""
    try:
        pay_slip = pay_slip_service.create_pay_slip(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(pay_slip)
    return pay_slip


# ---------------------------------------------------------------------------
# PATCH /payslips/{pay_slip_id}         — partial update
# ---------------------------------------------------------------------------


@router.patch("/{pay_slip_id}", response_model=PaySlipRead)
def update_pay_slip_endpoint(
    pay_slip_id: UUID,
    payload: PaySlipUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing pay slip record (partial — only supplied fields change)."""
    try:
        pay_slip = pay_slip_service.update_pay_slip(db, pay_slip_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(pay_slip)
    return pay_slip


# ---------------------------------------------------------------------------
# DELETE /payslips/{pay_slip_id}        — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{pay_slip_id}", status_code=204)
def delete_pay_slip_endpoint(
    pay_slip_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a pay slip record by ID."""
    try:
        pay_slip_service.delete_pay_slip(db, pay_slip_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()


# ---------------------------------------------------------------------------
# GET  /payslips/{year}/{month}/{employee_id}/pdf  — download PDF
# ---------------------------------------------------------------------------


@router.get("/{year}/{month}/{employee_id}/pdf")
def download_pay_slip_pdf(
    year: int = Path(..., ge=2000, le=2100, description="Period year"),  # noqa: B008
    month: int = Path(..., ge=1, le=12, description="Period month (1-12)"),  # noqa: B008
    employee_id: UUID = Path(..., description="Employee ID"),  # noqa: B008
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Download a pay slip PDF for a specific employee and period.

    Generates the PDF on-the-fly from the approved payroll data.
    Sets Content-Disposition for browser download.
    """
    try:
        pdf_bytes, filename = pay_slip_service.get_pay_slip_pdf_bytes(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            period_year=year,
            period_month=month,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)

    # Update downloaded_at on existing PaySlip record if present
    pay_slip_service.mark_downloaded(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        period_year=year,
        period_month=month,
    )
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# POST /payslips/{year}/{month}/generate-all     — batch generate
# ---------------------------------------------------------------------------


@router.post(
    "/{year}/{month}/generate-all",
    response_model=PaySlipGenerateAllResponse,
    status_code=201,
)
def generate_all_pay_slips_endpoint(
    year: int = Path(..., ge=2000, le=2100, description="Period year"),  # noqa: B008
    month: int = Path(..., ge=1, le=12, description="Period month (1-12)"),  # noqa: B008
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Batch-generate pay slip PDFs for all approved payrolls in a period.

    Generates PDF files on disk and creates PaySlip metadata records.
    Returns the count and list of generated pay slips.
    """
    try:
        pay_slips = pay_slip_service.generate_all_pay_slips(
            db,
            tenant_id=tenant_id,
            period_year=year,
            period_month=month,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    for ps in pay_slips:
        db.refresh(ps)
    return PaySlipGenerateAllResponse(
        count=len(pay_slips),
        pay_slips=pay_slips,
    )
