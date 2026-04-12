"""AuditLog API router — CRUD endpoints.

Provides GET (list / detail), POST (create), PATCH (partial update),
and DELETE for audit log entries.

Note: AuditLogUpdate restricts mutable fields to metadata only
(old_values, new_values, ip_address).  Core identity fields
(tenant_id, action, entity_type, entity_id) are immutable.

Prefix: /api/v1/audit-logs (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.audit_log import AuditLogCreate, AuditLogRead, AuditLogUpdate
from app.schemas.pagination import PaginatedResponse
from app.services import audit_log as audit_log_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Audit Logs"])


@router.get("", response_model=PaginatedResponse[AuditLogRead])
def list_entries(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    entity_type: str | None = Query(None, description="Filter by entity type"),  # noqa: B008
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),  # noqa: B008
    user_id: UUID | None = Query(None, description="Filter by user"),  # noqa: B008
    action: Literal["CREATE", "UPDATE", "DELETE"] | None = Query(  # noqa: B008
        None, description="Filter by action type"
    ),
    date_from: datetime | None = Query(  # noqa: B008
        None, description="Filter entries created at or after this timestamp (inclusive)"
    ),
    date_to: datetime | None = Query(  # noqa: B008
        None, description="Filter entries created at or before this timestamp (inclusive)"
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of audit log entries with optional filters."""
    filter_kwargs = {
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user_id": user_id,
        "action": action,
        "date_from": date_from,
        "date_to": date_to,
    }
    items = audit_log_service.list_audit_logs(db, skip=skip, limit=limit, **filter_kwargs)
    total = audit_log_service.count_audit_logs(db, **filter_kwargs)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{entry_id}", response_model=AuditLogRead)
def get_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single audit log entry by ID."""
    entry = audit_log_service.get_audit_log(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    return entry


@router.post("", response_model=AuditLogRead, status_code=201)
def create_entry(
    payload: AuditLogCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new audit log entry.

    Intended for internal / system use.  In production this endpoint
    should be protected by authentication middleware.
    """
    try:
        entry = audit_log_service.create_audit_log(db, payload)
        db.commit()
        db.refresh(entry)
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Audit log entry conflicts with existing data",
        ) from None
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        if any(kw in msg for kw in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from None
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return entry


@router.patch("/{entry_id}", response_model=AuditLogRead)
def update_entry(
    entry_id: UUID,
    payload: AuditLogUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Partially update an audit log entry (metadata fields only).

    Only old_values, new_values, and ip_address may be modified.
    Core identity fields (tenant_id, action, entity_type, entity_id)
    are immutable and cannot be changed.
    """
    try:
        entry = audit_log_service.update_audit_log(db, entry_id, payload)
        if entry is None:
            raise HTTPException(status_code=404, detail="Audit log entry not found")
        db.commit()
        db.refresh(entry)
    except HTTPException:
        raise
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Audit log entry conflicts with existing data",
        ) from None
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        if any(kw in msg for kw in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from None
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete an audit log entry by ID."""
    try:
        deleted = audit_log_service.delete_audit_log(db, entry_id)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete audit log entry: dependent records exist",
        ) from None
    if not deleted:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    db.commit()
