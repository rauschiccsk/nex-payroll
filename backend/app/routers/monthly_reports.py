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
from app.services.monthly_report import (
    count_monthly_reports,
    create_monthly_report,
    delete_monthly_report,
    get_monthly_report,
    list_monthly_reports,
    update_monthly_report,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Monthly Reports"])


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
    try:
        items = list_monthly_reports(
            db,
            tenant_id=tenant_id,
            report_type=report_type,
            status=status,
            period_year=period_year,
            period_month=period_month,
            skip=skip,
            limit=limit,
        )
        total = count_monthly_reports(
            db,
            tenant_id=tenant_id,
            report_type=report_type,
            status=status,
            period_year=period_year,
            period_month=period_month,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{report_id}", response_model=MonthlyReportRead)
def get_monthly_report_endpoint(
    report_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single monthly report by ID."""
    report = get_monthly_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Monthly report not found")
    return report


@router.post("", response_model=MonthlyReportRead, status_code=201)
def create_monthly_report_endpoint(
    payload: MonthlyReportCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new monthly report record."""
    try:
        report = create_monthly_report(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(report)
    return report


@router.put("/{report_id}", response_model=MonthlyReportRead)
def update_monthly_report_endpoint(
    report_id: UUID,
    payload: MonthlyReportUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing monthly report record."""
    try:
        report = update_monthly_report(db, report_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}", status_code=204)
def delete_monthly_report_endpoint(
    report_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a monthly report by ID."""
    try:
        delete_monthly_report(db, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
