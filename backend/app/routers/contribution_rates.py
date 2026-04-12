"""ContributionRate API router — CRUD endpoints.

Prefix: /api/v1/contribution-rates (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.contribution_rate import (
    ContributionRateCreate,
    ContributionRateRead,
    ContributionRateUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services import contribution_rate as contribution_rate_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Contribution Rates"])


@router.get("", response_model=PaginatedResponse[ContributionRateRead])
def list_rates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    rate_type: str | None = Query(None, description="Filter by rate type, e.g. sp_employee_nemocenske"),
    payer: str | None = Query(None, description="Filter by payer: employee or employer"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of contribution rates with optional filters."""
    items = contribution_rate_service.list_contribution_rates(
        db, skip=skip, limit=limit, rate_type=rate_type, payer=payer
    )
    total = contribution_rate_service.count_contribution_rates(db, rate_type=rate_type, payer=payer)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{rate_id}", response_model=ContributionRateRead)
def get_rate(
    rate_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single contribution rate by ID."""
    rate = contribution_rate_service.get_contribution_rate(db, rate_id)
    if rate is None:
        raise HTTPException(status_code=404, detail="Contribution rate not found")
    return rate


@router.post("", response_model=ContributionRateRead, status_code=201)
def create_rate(
    payload: ContributionRateCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new contribution rate."""
    try:
        rate = contribution_rate_service.create_contribution_rate(db, payload)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if any(w in msg for w in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(rate)
    return rate


@router.patch("/{rate_id}", response_model=ContributionRateRead)
def update_rate(
    rate_id: UUID,
    payload: ContributionRateUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing contribution rate."""
    try:
        rate = contribution_rate_service.update_contribution_rate(db, rate_id, payload)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if any(w in msg for w in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if rate is None:
        raise HTTPException(status_code=404, detail="Contribution rate not found")
    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}", status_code=204)
def delete_rate(
    rate_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a contribution rate by ID."""
    try:
        deleted = contribution_rate_service.delete_contribution_rate(db, rate_id)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if any(w in msg for w in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Contribution rate not found")
    db.commit()
