"""MonthlyReport API router — CRUD endpoints.

Prefix: /api/v1/monthly-reports (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.monthly_report import (
    MonthlyReportCreate,
    MonthlyReportRead,
    MonthlyReportUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services import monthly_report as monthly_report_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Monthly Reports"])


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
# GET  /monthly-reports          — paginated list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[MonthlyReportRead])
def list_monthly_reports_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    report_type: str | None = Query(None, description="Filter by report type"),  # noqa: B008
    status: str | None = Query(None, description="Filter by status"),  # noqa: B008
    period_year: int | None = Query(None, ge=2000, le=2100, description="Filter by period year"),  # noqa: B008
    period_month: int | None = Query(None, ge=1, le=12, description="Filter by period month"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of monthly reports."""
    items = monthly_report_service.list_monthly_reports(
        db,
        tenant_id=tenant_id,
        report_type=report_type,
        status=status,
        period_year=period_year,
        period_month=period_month,
        skip=skip,
        limit=limit,
    )
    total = monthly_report_service.count_monthly_reports(
        db,
        tenant_id=tenant_id,
        report_type=report_type,
        status=status,
        period_year=period_year,
        period_month=period_month,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /monthly-reports/{id}     — detail
# ---------------------------------------------------------------------------


@router.get("/{report_id}", response_model=MonthlyReportRead)
def get_monthly_report_endpoint(
    report_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single monthly report by ID."""
    report = monthly_report_service.get_monthly_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Monthly report not found")
    return report


# ---------------------------------------------------------------------------
# POST /monthly-reports          — create
# ---------------------------------------------------------------------------


@router.post("", response_model=MonthlyReportRead, status_code=201)
def create_monthly_report_endpoint(
    payload: MonthlyReportCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new monthly report record."""
    try:
        report = monthly_report_service.create_monthly_report(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# PATCH /monthly-reports/{id}    — partial update
# ---------------------------------------------------------------------------


@router.patch("/{report_id}", response_model=MonthlyReportRead)
def update_monthly_report_endpoint(
    report_id: UUID,
    payload: MonthlyReportUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing monthly report record (partial — only supplied fields change)."""
    try:
        report = monthly_report_service.update_monthly_report(db, report_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# DELETE /monthly-reports/{id}   — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{report_id}", status_code=204)
def delete_monthly_report_endpoint(
    report_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a monthly report by ID."""
    try:
        monthly_report_service.delete_monthly_report(db, report_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
