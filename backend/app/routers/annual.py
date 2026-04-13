"""Annual processing API router — annual tax settlement, income certificates, tax report.

Prefix: /api/v1/annual (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.

Implements DESIGN.md §6.14:
  POST /api/v1/annual/{year}/tax-settlement              — Calculate settlement
  GET  /api/v1/annual/{year}/income-certificate/{eid}/pdf — Download certificate
  POST /api/v1/annual/{year}/tax-report                  — Generate annual report
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.annual_settlement import (
    AnnualSettlementListResponse,
    AnnualSettlementRequest,
    AnnualSettlementResponse,
    AnnualTaxReportRequest,
    AnnualTaxReportResponse,
    ApproveSettlementRequest,
    ApproveSettlementResponse,
    EmployeeSettlementResult,
)
from app.services import annual_settlement as annual_settlement_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Annual Processing"])


# ---------------------------------------------------------------------------
# POST /annual/{year}/tax-settlement — calculate annual settlement
# ---------------------------------------------------------------------------


@router.post("/{year}/tax-settlement", response_model=AnnualSettlementResponse)
def calculate_settlement_endpoint(
    year: int,
    payload: AnnualSettlementRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Calculate annual tax settlement for all employees.

    Director only. Recalculates NČZD using annual rules and compares
    actual annual tax liability against sum of monthly advances.
    """
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    try:
        settlements = annual_settlement_service.calculate_annual_settlement(
            db,
            tenant_id=payload.tenant_id,
            year=year,
        )
        db.commit()

        # Refresh to get server-generated fields
        for s in settlements:
            db.refresh(s)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    total_overpaid = sum(s.settlement_amount for s in settlements if s.settlement_amount > 0)
    total_underpaid = sum(s.settlement_amount for s in settlements if s.settlement_amount < 0)

    return AnnualSettlementResponse(
        year=year,
        tenant_id=payload.tenant_id,
        total_employees=len(settlements),
        total_overpaid=total_overpaid,
        total_underpaid=total_underpaid,
        settlements=[EmployeeSettlementResult.model_validate(s) for s in settlements],
    )


# ---------------------------------------------------------------------------
# GET /annual/{year}/settlements — list settlements for a year
# ---------------------------------------------------------------------------


@router.get("/{year}/settlements", response_model=AnnualSettlementListResponse)
def list_settlements_endpoint(
    year: int,
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """List all annual settlements for a tenant/year.

    Director or Accountant. Returns calculated settlements for review.
    """
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    settlements = annual_settlement_service.get_settlements_for_year(db, tenant_id=tenant_id, year=year)

    return AnnualSettlementListResponse(
        year=year,
        tenant_id=tenant_id,
        total_employees=len(settlements),
        settlements=[EmployeeSettlementResult.model_validate(s) for s in settlements],
    )


# ---------------------------------------------------------------------------
# POST /annual/{year}/settlements/{settlement_id}/approve — approve settlement
# ---------------------------------------------------------------------------


@router.post(
    "/{year}/settlements/{settlement_id}/approve",
    response_model=ApproveSettlementResponse,
)
def approve_settlement_endpoint(
    year: int,
    settlement_id: UUID,
    payload: ApproveSettlementRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Approve an annual tax settlement.

    Director only. Transitions status from 'calculated' to 'approved'.
    """
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    try:
        settlement = annual_settlement_service.approve_settlement(
            db,
            settlement_id=settlement_id,
            tenant_id=payload.tenant_id,
            approved_by=payload.approved_by,
        )
        db.commit()
        db.refresh(settlement)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ApproveSettlementResponse.model_validate(settlement)


# ---------------------------------------------------------------------------
# GET /annual/{year}/income-certificate/{employee_id}/pdf — download cert
# ---------------------------------------------------------------------------


@router.get("/{year}/income-certificate/{employee_id}/pdf")
def download_income_certificate_endpoint(
    year: int,
    employee_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Download income certificate (Potvrdenie o príjmoch) PDF.

    Director or Accountant. Requires annual settlement to be calculated first.
    """
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    try:
        pdf_bytes = annual_settlement_service.generate_income_certificate_pdf(
            db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            year=year,
        )
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = f"potvrdenie_prijmov_{year}_{employee_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /annual/{year}/tax-report — generate annual tax report summary
# ---------------------------------------------------------------------------


@router.post("/{year}/tax-report", response_model=AnnualTaxReportResponse)
def generate_tax_report_endpoint(
    year: int,
    payload: AnnualTaxReportRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Generate annual tax report summary (Hlásenie o dani).

    Director only. Aggregates settlement data for annual tax filing.
    Requires annual settlement to be calculated first.
    """
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    try:
        report_data = annual_settlement_service.generate_annual_tax_report_summary(
            db,
            tenant_id=payload.tenant_id,
            year=year,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AnnualTaxReportResponse(**report_data)
