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
from app.services.contribution_rate import (
    count_contribution_rates,
    create_contribution_rate,
    delete_contribution_rate,
    get_contribution_rate,
    list_contribution_rates,
    update_contribution_rate,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Contribution Rates"])


@router.get("", response_model=PaginatedResponse[ContributionRateRead])
def list_rates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of contribution rates."""
    items = list_contribution_rates(db, skip=skip, limit=limit)
    total = count_contribution_rates(db)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{rate_id}", response_model=ContributionRateRead)
def get_rate(
    rate_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single contribution rate by ID."""
    rate = get_contribution_rate(db, rate_id)
    if rate is None:
        raise HTTPException(status_code=404, detail="Contribution rate not found")
    return rate


@router.post("", response_model=ContributionRateRead, status_code=201)
def create_rate(
    payload: ContributionRateCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new contribution rate."""
    rate = create_contribution_rate(db, payload)
    db.commit()
    db.refresh(rate)
    return rate


@router.put("/{rate_id}", response_model=ContributionRateRead)
def update_rate(
    rate_id: UUID,
    payload: ContributionRateUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing contribution rate."""
    rate = update_contribution_rate(db, rate_id, payload)
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
    deleted = delete_contribution_rate(db, rate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contribution rate not found")
    db.commit()
