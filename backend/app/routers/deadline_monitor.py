"""Deadline monitoring API router.

Prefix: /api/v1/deadline-monitor (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.

Provides endpoints for deadline monitoring and notification generation:
  POST /check           — Check and generate deadline notifications
  GET  /upcoming        — List upcoming deadlines (dashboard)
  POST /cleanup         — Clean up old notifications
"""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["Deadline Monitor"])

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request/Response schemas (inline — specific to deadline monitor endpoints)
# ---------------------------------------------------------------------------


class DeadlineCheckRequest(BaseModel):
    """Request to check upcoming deadlines and create notifications."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    reference_date: date | None = Field(
        default=None,
        description="Reference date for checking deadlines (defaults to today)",
    )


class DeadlineCheckResponse(BaseModel):
    """Response after checking deadlines."""

    notifications_created: int
    reference_date: str


class UpcomingDeadlineItem(BaseModel):
    """Single upcoming deadline."""

    deadline_id: str
    code: str
    name: str
    institution: str
    deadline_type: str
    next_date: str
    days_until: int
    severity: str


class UpcomingDeadlinesResponse(BaseModel):
    """List of upcoming deadlines."""

    items: list[UpcomingDeadlineItem]
    total: int
    days_ahead: int


class CleanupRequest(BaseModel):
    """Request to clean up old notifications."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    max_age_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Delete notifications older than this many days",
    )


class CleanupResponse(BaseModel):
    """Response after cleanup."""

    deleted_count: int
    max_age_days: int


# ---------------------------------------------------------------------------
# POST /check — check deadlines and create notifications
# ---------------------------------------------------------------------------


@router.post("/check", response_model=DeadlineCheckResponse)
def check_deadlines_endpoint(
    payload: DeadlineCheckRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Check statutory deadlines and generate notifications for upcoming ones.

    Creates notifications for directors and accountants in the tenant
    when deadlines are 7, 3, or 1 day(s) away.  Duplicate notifications
    are automatically skipped.
    """
    from app.services.deadline_monitor import check_upcoming_deadlines

    try:
        notifications = check_upcoming_deadlines(
            db,
            tenant_id=payload.tenant_id,
            reference_date=payload.reference_date,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ref = payload.reference_date or date.today()
    return DeadlineCheckResponse(
        notifications_created=len(notifications),
        reference_date=ref.isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /upcoming — list upcoming deadlines (dashboard)
# ---------------------------------------------------------------------------


@router.get("/upcoming", response_model=UpcomingDeadlinesResponse)
def list_upcoming_deadlines_endpoint(
    days_ahead: int = Query(default=30, ge=1, le=365, description="Days to look ahead"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """List upcoming statutory deadlines within the specified window.

    Does NOT create notifications — intended for dashboard display.
    """
    from app.services.deadline_monitor import get_upcoming_deadlines

    items = get_upcoming_deadlines(db, days_ahead=days_ahead)

    return UpcomingDeadlinesResponse(
        items=[UpcomingDeadlineItem(**item) for item in items],
        total=len(items),
        days_ahead=days_ahead,
    )


# ---------------------------------------------------------------------------
# POST /cleanup — clean up old notifications
# ---------------------------------------------------------------------------


@router.post("/cleanup", response_model=CleanupResponse)
def cleanup_notifications_endpoint(
    payload: CleanupRequest,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete notifications older than the specified age.

    Per DESIGN.md §5.13: auto-cleanup notifications older than 90 days.
    """
    from app.services.deadline_monitor import cleanup_old_notifications

    try:
        count = cleanup_old_notifications(
            db,
            tenant_id=payload.tenant_id,
            max_age_days=payload.max_age_days,
        )
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CleanupResponse(
        deleted_count=count,
        max_age_days=payload.max_age_days,
    )
