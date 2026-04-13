"""NEX Ledger sync API router.

Prefix: /api/v1/ledger-sync (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.

Provides endpoints to manage payroll-to-ledger synchronisation status:
  GET  /status          — Get sync status summary for a period
  POST /mark            — Mark approved payrolls for sync
  POST /complete        — Mark pending payrolls as synced
  POST /error           — Mark pending payrolls as error
  GET  /pending         — List payrolls pending sync
  PATCH /{payroll_id}   — Update single payroll sync status
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.payroll import PayrollRead

router = APIRouter(tags=["Ledger Sync"])

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request/Response schemas (inline — specific to ledger sync endpoints)
# ---------------------------------------------------------------------------


class LedgerSyncStatusResponse(BaseModel):
    """Summary of ledger sync statuses for a period."""

    tenant_id: str
    period_year: int
    period_month: int
    total: int
    pending: int
    synced: int
    error: int
    not_synced: int


class LedgerSyncMarkRequest(BaseModel):
    """Request to mark payrolls for sync."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    period_year: int = Field(..., ge=2000, le=2100, description="Period year")
    period_month: int = Field(..., ge=1, le=12, description="Period month")


class LedgerSyncMarkResponse(BaseModel):
    """Response after marking payrolls."""

    updated_count: int
    period_year: int
    period_month: int


class LedgerSyncUpdateRequest(BaseModel):
    """Request to update a single payroll's sync status."""

    new_status: str = Field(
        ...,
        description="New ledger sync status: pending, synced, error",
    )


# ---------------------------------------------------------------------------
# GET /status — sync status summary
# ---------------------------------------------------------------------------


@router.get("/status", response_model=LedgerSyncStatusResponse)
def get_sync_status_endpoint(
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    period_year: int = Query(..., ge=2000, le=2100, description="Period year"),  # noqa: B008
    period_month: int = Query(..., ge=1, le=12, description="Period month"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Get summary of ledger sync statuses for all payrolls in a period."""
    from app.services.ledger_sync import get_sync_status

    status = get_sync_status(
        db,
        tenant_id=tenant_id,
        period_year=period_year,
        period_month=period_month,
    )
    return LedgerSyncStatusResponse(**status)


# ---------------------------------------------------------------------------
# POST /mark — mark approved payrolls for sync
# ---------------------------------------------------------------------------


@router.post("/mark", response_model=LedgerSyncMarkResponse)
def mark_for_sync_endpoint(
    payload: LedgerSyncMarkRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Mark all approved payrolls in a period as pending for ledger sync."""
    from app.services.ledger_sync import mark_for_sync

    try:
        count = mark_for_sync(
            db,
            tenant_id=payload.tenant_id,
            period_year=payload.period_year,
            period_month=payload.period_month,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return LedgerSyncMarkResponse(
        updated_count=count,
        period_year=payload.period_year,
        period_month=payload.period_month,
    )


# ---------------------------------------------------------------------------
# POST /complete — bulk mark pending as synced
# ---------------------------------------------------------------------------


@router.post("/complete", response_model=LedgerSyncMarkResponse)
def complete_sync_endpoint(
    payload: LedgerSyncMarkRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Mark all pending payrolls in a period as synced."""
    from app.services.ledger_sync import bulk_update_sync_status

    try:
        count = bulk_update_sync_status(
            db,
            tenant_id=payload.tenant_id,
            period_year=payload.period_year,
            period_month=payload.period_month,
            new_status="synced",
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return LedgerSyncMarkResponse(
        updated_count=count,
        period_year=payload.period_year,
        period_month=payload.period_month,
    )


# ---------------------------------------------------------------------------
# POST /error — bulk mark pending as error
# ---------------------------------------------------------------------------


@router.post("/error", response_model=LedgerSyncMarkResponse)
def error_sync_endpoint(
    payload: LedgerSyncMarkRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Mark all pending payrolls in a period as error (sync failed)."""
    from app.services.ledger_sync import bulk_update_sync_status

    try:
        count = bulk_update_sync_status(
            db,
            tenant_id=payload.tenant_id,
            period_year=payload.period_year,
            period_month=payload.period_month,
            new_status="error",
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return LedgerSyncMarkResponse(
        updated_count=count,
        period_year=payload.period_year,
        period_month=payload.period_month,
    )


# ---------------------------------------------------------------------------
# GET /pending — list pending payrolls
# ---------------------------------------------------------------------------


@router.get("/pending")
def list_pending_endpoint(
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    period_year: int | None = Query(default=None, ge=2000, le=2100),  # noqa: B008
    period_month: int | None = Query(default=None, ge=1, le=12),  # noqa: B008
    skip: int = Query(default=0, ge=0),  # noqa: B008
    limit: int = Query(default=50, le=100),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """List payrolls with ledger_sync_status='pending'."""
    from app.services.ledger_sync import count_pending, list_pending

    items = list_pending(
        db,
        tenant_id=tenant_id,
        period_year=period_year,
        period_month=period_month,
        skip=skip,
        limit=limit,
    )
    total = count_pending(
        db,
        tenant_id=tenant_id,
        period_year=period_year,
        period_month=period_month,
    )

    return {
        "items": [PayrollRead.model_validate(p) for p in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


# ---------------------------------------------------------------------------
# PATCH /{payroll_id} — update single payroll sync status
# ---------------------------------------------------------------------------


@router.patch("/{payroll_id}")
def update_sync_status_endpoint(
    payroll_id: UUID,
    payload: LedgerSyncUpdateRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update ledger sync status for a single payroll."""
    from app.services.ledger_sync import update_sync_status

    try:
        payroll = update_sync_status(
            db,
            payroll_id=payroll_id,
            new_status=payload.new_status,
        )
        db.commit()
        db.refresh(payroll)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PayrollRead.model_validate(payroll)
