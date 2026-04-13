"""NEX Ledger integration API router.

Prefix: /api/v1/integration/ledger (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.

Implements DESIGN.md §6.15:
  POST /api/v1/integration/ledger/{year}/{month}/sync   — Sync to ledger
  GET  /api/v1/integration/ledger/{year}/{month}/status  — Sync status
  GET  /api/v1/integration/ledger/{year}/{month}/entries — List journal entries
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.journal_entry import (
    JournalEntryRead,
    LedgerSyncRequest,
    LedgerSyncResponse,
    LedgerSyncStatusResponse,
)
from app.services import journal_entry as journal_entry_service

router = APIRouter(tags=["NEX Ledger Integration"])

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# POST /{year}/{month}/sync — sync payroll journal entries to ledger
# ---------------------------------------------------------------------------


@router.post("/{year}/{month}/sync", response_model=LedgerSyncResponse)
def sync_to_ledger_endpoint(
    year: int,
    month: int,
    payload: LedgerSyncRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Generate journal entries from approved payrolls and sync to NEX Ledger.

    Director only. Creates double-entry accounting records for the period.
    Existing entries for re-synced payrolls are replaced.
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="Month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    try:
        result = journal_entry_service.sync_period(
            db,
            tenant_id=payload.tenant_id,
            period_year=year,
            period_month=month,
        )
        db.commit()
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg or ("no " in msg and "found" in msg):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if any(kw in msg for kw in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info(
        "Ledger sync completed: %d entries for %d/%02d (batch=%s)",
        result["entries_created"],
        year,
        month,
        result["sync_batch_id"],
    )

    return LedgerSyncResponse(**result)


# ---------------------------------------------------------------------------
# GET /{year}/{month}/status — sync status for a period
# ---------------------------------------------------------------------------


@router.get("/{year}/{month}/status", response_model=LedgerSyncStatusResponse)
def get_sync_status_endpoint(
    year: int,
    month: int,
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Get integration sync status for a period.

    Director only. Returns payroll sync counts and journal entry totals.
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="Month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    status = journal_entry_service.get_period_status(
        db,
        tenant_id=tenant_id,
        period_year=year,
        period_month=month,
    )
    return LedgerSyncStatusResponse(**status)


# ---------------------------------------------------------------------------
# GET /{year}/{month}/entries — list journal entries for a period
# ---------------------------------------------------------------------------


@router.get("/{year}/{month}/entries", response_model=list[JournalEntryRead])
def list_entries_endpoint(
    year: int,
    month: int,
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """List all journal entries for a period.

    Director only. Returns detailed journal entry lines.
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="Month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="Year must be between 2000 and 2100")

    entries = journal_entry_service.get_entries_for_period(
        db,
        tenant_id=tenant_id,
        period_year=year,
        period_month=month,
    )
    return [JournalEntryRead.model_validate(e) for e in entries]
