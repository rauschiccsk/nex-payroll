"""MonthlyReport API router — CRUD + SP/ZP report generation endpoints.

Prefix: /api/v1/monthly-reports (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.monthly_report import (
    MonthlyReportCreate,
    MonthlyReportRead,
    MonthlyReportUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services import monthly_report as monthly_report_service
from app.services.sp_report_generator import generate_sp_report_xml, get_sp_report_deadline
from app.services.zp_report_generator import (
    REPORT_TYPE_TO_INSTITUTION,
    REPORT_TYPE_TO_INSURER_CODE,
    generate_zp_report_xml,
    get_zp_report_deadline,
)

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


# ---------------------------------------------------------------------------
# POST /monthly-reports/{tenant_id}/{year}/{month}/sp-xml — generate SP report
# ---------------------------------------------------------------------------


@router.post(
    "/{tenant_id}/{year}/{month}/sp-xml",
    response_model=MonthlyReportRead,
    status_code=201,
)
def generate_sp_report_endpoint(
    tenant_id: UUID,
    year: int,
    month: int,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Generate SP monthly report XML and store a MonthlyReport record.

    Builds the XML from approved/paid payrolls for the given period,
    then creates a ``monthly_reports`` record with ``report_type='sp_monthly'``.
    Returns the MonthlyReport metadata (the XML is downloadable via the GET endpoint).
    """
    try:
        xml_bytes = generate_sp_report_xml(db, tenant_id, year, month)
    except ValueError as exc:
        _raise_for_value_error(exc)

    deadline = get_sp_report_deadline(year, month)
    file_path = f"/data/reports/{year}/{month:02d}/sp_monthly_{tenant_id}.xml"

    payload = MonthlyReportCreate(
        tenant_id=tenant_id,
        period_year=year,
        period_month=month,
        report_type="sp_monthly",
        file_path=file_path,
        file_format="xml",
        status="generated",
        deadline_date=deadline,
        institution="Sociálna poisťovňa",
    )

    try:
        report = monthly_report_service.create_monthly_report(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)

    db.commit()
    db.refresh(report)

    logger.info(
        "SP monthly report generated: tenant=%s period=%d/%02d size=%d bytes",
        tenant_id,
        year,
        month,
        len(xml_bytes),
    )

    return report


# ---------------------------------------------------------------------------
# GET /monthly-reports/{tenant_id}/{year}/{month}/sp-xml — download SP XML
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/{year}/{month}/sp-xml")
def download_sp_report_endpoint(
    tenant_id: UUID,
    year: int,
    month: int,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Download SP monthly report as XML.

    Generates the XML on the fly from approved/paid payrolls.
    Does not create or modify any database records.
    """
    try:
        xml_bytes = generate_sp_report_xml(db, tenant_id, year, month)
    except ValueError as exc:
        _raise_for_value_error(exc)

    filename = f"sp_monthly_{year}_{month:02d}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /monthly-reports/{tenant_id}/{year}/{month}/zp-xml/{report_type}
#      — generate ZP report per health insurer
# ---------------------------------------------------------------------------


@router.post(
    "/{tenant_id}/{year}/{month}/zp-xml/{report_type}",
    response_model=MonthlyReportRead,
    status_code=201,
)
def generate_zp_report_endpoint(
    tenant_id: UUID,
    year: int,
    month: int,
    report_type: str,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Generate ZP monthly report XML for a specific health insurer.

    Builds the XML from approved/paid payrolls for the given period,
    filtering only employees assigned to the specified health insurer.
    Creates a ``monthly_reports`` record with the appropriate ZP report type.
    Returns the MonthlyReport metadata (XML downloadable via the GET endpoint).

    ``report_type`` must be one of: ``zp_vszp``, ``zp_dovera``, ``zp_union``.
    """
    if report_type not in REPORT_TYPE_TO_INSURER_CODE:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid ZP report type: {report_type}. "
            f"Must be one of: {', '.join(sorted(REPORT_TYPE_TO_INSURER_CODE))}",
        )

    try:
        xml_bytes, health_insurer_id = generate_zp_report_xml(
            db,
            tenant_id,
            year,
            month,
            report_type,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)

    deadline = get_zp_report_deadline(year, month)
    institution = REPORT_TYPE_TO_INSTITUTION[report_type]
    file_path = f"/data/reports/{year}/{month:02d}/{report_type}_{tenant_id}.xml"

    payload = MonthlyReportCreate(
        tenant_id=tenant_id,
        period_year=year,
        period_month=month,
        report_type=report_type,
        file_path=file_path,
        file_format="xml",
        status="generated",
        deadline_date=deadline,
        institution=institution,
        health_insurer_id=health_insurer_id,
    )

    try:
        report = monthly_report_service.create_monthly_report(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)

    db.commit()
    db.refresh(report)

    logger.info(
        "ZP monthly report generated (%s): tenant=%s period=%d/%02d size=%d bytes",
        report_type,
        tenant_id,
        year,
        month,
        len(xml_bytes),
    )

    return report


# ---------------------------------------------------------------------------
# GET /monthly-reports/{tenant_id}/{year}/{month}/zp-xml/{report_type}
#     — download ZP XML
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}/{year}/{month}/zp-xml/{report_type}")
def download_zp_report_endpoint(
    tenant_id: UUID,
    year: int,
    month: int,
    report_type: str,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Download ZP monthly report as XML for a specific health insurer.

    Generates the XML on the fly from approved/paid payrolls.
    Does not create or modify any database records.

    ``report_type`` must be one of: ``zp_vszp``, ``zp_dovera``, ``zp_union``.
    """
    if report_type not in REPORT_TYPE_TO_INSURER_CODE:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid ZP report type: {report_type}. "
            f"Must be one of: {', '.join(sorted(REPORT_TYPE_TO_INSURER_CODE))}",
        )

    try:
        xml_bytes, _insurer_id = generate_zp_report_xml(
            db,
            tenant_id,
            year,
            month,
            report_type,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)

    filename = f"{report_type}_{year}_{month:02d}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
