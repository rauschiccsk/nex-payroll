"""Payroll API router — CRUD endpoints.

Prefix: /api/v1/payroll (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.calculation import PayrollCalculateRequest, PayrollCalculationResult
from app.schemas.pagination import PaginatedResponse
from app.schemas.payroll import PayrollCreate, PayrollRead, PayrollUpdate
from app.services import payroll as payroll_service
from app.services.calculation_engine import calculate_employee_payroll, persist_calculation

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
# POST /payroll/calculate              — trigger payroll calculation
# ---------------------------------------------------------------------------


@router.post("/calculate", response_model=PayrollCalculationResult, status_code=200)
def calculate_payroll_endpoint(
    payload: PayrollCalculateRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Calculate monthly payroll (gross → net) for an employee.

    Fetches employee data, contract, children, and rates from DB.
    Creates or updates a Payroll record with status='calculated'.
    Returns the complete calculation breakdown.
    """
    try:
        result = calculate_employee_payroll(
            db,
            tenant_id=payload.tenant_id,
            employee_id=payload.employee_id,
            contract_id=payload.contract_id,
            period_year=payload.period_year,
            period_month=payload.period_month,
            overtime_hours=payload.overtime_hours,
            overtime_amount=payload.overtime_amount,
            bonus_amount=payload.bonus_amount,
            supplement_amount=payload.supplement_amount,
        )
        # Persist the calculation result
        persist_calculation(db, tenant_id=payload.tenant_id, result=result)
        db.commit()
    except ValueError as exc:
        _raise_for_value_error(exc)

    return PayrollCalculationResult(
        base_wage=result.base_wage,
        overtime_hours=result.overtime_hours,
        overtime_amount=result.overtime_amount,
        bonus_amount=result.bonus_amount,
        supplement_amount=result.supplement_amount,
        gross_wage=result.gross_wage,
        sp_assessment_base=result.sp_assessment_base,
        sp_nemocenske=result.sp_nemocenske,
        sp_starobne=result.sp_starobne,
        sp_invalidne=result.sp_invalidne,
        sp_nezamestnanost=result.sp_nezamestnanost,
        sp_employee_total=result.sp_employee_total,
        zp_assessment_base=result.zp_assessment_base,
        zp_employee=result.zp_employee,
        partial_tax_base=result.partial_tax_base,
        nczd_applied=result.nczd_applied,
        tax_base=result.tax_base,
        tax_advance=result.tax_advance,
        child_bonus=result.child_bonus,
        child_bonus_details=[
            {
                "child_id": c.child_id,
                "child_name": c.child_name,
                "age": c.age,
                "bonus_amount": c.bonus_amount,
            }
            for c in result.child_bonus_details
        ],
        tax_after_bonus=result.tax_after_bonus,
        net_wage=result.net_wage,
        sp_employer_nemocenske=result.sp_employer_nemocenske,
        sp_employer_starobne=result.sp_employer_starobne,
        sp_employer_invalidne=result.sp_employer_invalidne,
        sp_employer_nezamestnanost=result.sp_employer_nezamestnanost,
        sp_employer_garancne=result.sp_employer_garancne,
        sp_employer_rezervny=result.sp_employer_rezervny,
        sp_employer_kurzarbeit=result.sp_employer_kurzarbeit,
        sp_employer_urazove=result.sp_employer_urazove,
        sp_employer_total=result.sp_employer_total,
        zp_employer=result.zp_employer,
        pillar2_amount=result.pillar2_amount,
        total_employer_cost=result.total_employer_cost,
        period_year=result.period_year,
        period_month=result.period_month,
        employee_id=result.employee_id,
        contract_id=result.contract_id,
        effective_date=result.effective_date,
    )


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
