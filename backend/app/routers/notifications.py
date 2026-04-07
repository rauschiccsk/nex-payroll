"""Notification API router — CRUD endpoints.

Prefix: /api/v1/notifications (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.notification import NotificationCreate, NotificationRead, NotificationUpdate
from app.schemas.pagination import PaginatedResponse
from app.services import notification as notification_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Notifications"])


@router.get("", response_model=PaginatedResponse[NotificationRead])
def list_notifications_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    user_id: UUID | None = Query(None, description="Filter by user"),  # noqa: B008
    is_read: bool | None = Query(None, description="Filter by read status"),  # noqa: B008
    type: str | None = Query(None, description="Filter by type (deadline, anomaly, system, approval)"),  # noqa: B008, A002
    severity: str | None = Query(None, description="Filter by severity (info, warning, critical)"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of notifications."""
    items = notification_service.list_notifications(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        is_read=is_read,
        type=type,
        severity=severity,
        skip=skip,
        limit=limit,
    )
    total = notification_service.count_notifications(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        is_read=is_read,
        type=type,
        severity=severity,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{notification_id}", response_model=NotificationRead)
def get_notification_endpoint(
    notification_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single notification by ID."""
    notification = notification_service.get_notification(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


def _raise_for_value_error(exc: ValueError) -> None:
    """Map ValueError message text to the appropriate HTTP status code."""
    msg = str(exc).lower()
    if "not found" in msg:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if any(kw in msg for kw in ("duplicate", "conflict", "already exists")):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    # invalid, constraint, foreign key, or anything else → 422
    raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("", response_model=NotificationRead, status_code=201)
def create_notification_endpoint(
    payload: NotificationCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new notification."""
    try:
        notification = notification_service.create_notification(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/{notification_id}", response_model=NotificationRead)
def update_notification_endpoint(
    notification_id: UUID,
    payload: NotificationUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing notification."""
    try:
        notification = notification_service.update_notification(db, notification_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(notification)
    return notification


@router.delete("/{notification_id}", status_code=204)
def delete_notification_endpoint(
    notification_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a notification by ID."""
    try:
        notification_service.delete_notification(db, notification_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
