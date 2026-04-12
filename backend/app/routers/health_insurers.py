"""HealthInsurer API router — CRUD endpoints.

Prefix: /api/v1/health-insurers (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.health_insurer import (
    HealthInsurerCreate,
    HealthInsurerRead,
    HealthInsurerUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services import health_insurer as health_insurer_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health Insurers"])


@router.get("", response_model=PaginatedResponse[HealthInsurerRead])
def list_insurers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of health insurers with optional filters."""
    items = health_insurer_service.list_health_insurers(db, skip=skip, limit=limit, is_active=is_active)
    total = health_insurer_service.count_health_insurers(db, is_active=is_active)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{insurer_id}", response_model=HealthInsurerRead)
def get_insurer(
    insurer_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single health insurer by ID."""
    insurer = health_insurer_service.get_health_insurer(db, insurer_id)
    if insurer is None:
        raise HTTPException(status_code=404, detail="Health insurer not found")
    return insurer


@router.post("", response_model=HealthInsurerRead, status_code=201)
def create_insurer(
    payload: HealthInsurerCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new health insurer."""
    try:
        insurer = health_insurer_service.create_health_insurer(db, payload)
        db.commit()
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Health insurer with code '{payload.code}' already exists",
        ) from None
    db.refresh(insurer)
    return insurer


@router.patch("/{insurer_id}", response_model=HealthInsurerRead)
def update_insurer(
    insurer_id: UUID,
    payload: HealthInsurerUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing health insurer."""
    try:
        insurer = health_insurer_service.update_health_insurer(db, insurer_id, payload)
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Health insurer with duplicate code or name already exists",
        ) from None
    if insurer is None:
        raise HTTPException(status_code=404, detail="Health insurer not found")
    db.commit()
    db.refresh(insurer)
    return insurer


@router.delete("/{insurer_id}", status_code=204)
def delete_insurer(
    insurer_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a health insurer by ID."""
    deleted = health_insurer_service.delete_health_insurer(db, insurer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Health insurer not found")
    db.commit()
