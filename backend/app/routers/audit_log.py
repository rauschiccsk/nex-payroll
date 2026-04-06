"""AuditLog API router — read-only endpoints.

Prefix: /api/v1/audit-logs (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.

Audit log entries are immutable — created internally by the system.
No POST, PUT, or DELETE endpoints are exposed.
"""

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.audit_log import AuditLogRead
from app.schemas.pagination import PaginatedResponse
from app.services.audit_log import (
    count_audit_logs,
    get_audit_log,
    list_audit_logs,
)

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
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of audit log entries with optional filters."""
    items = list_audit_logs(
        db,
        skip=skip,
        limit=limit,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
    )
    total = count_audit_logs(
        db,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{entry_id}", response_model=AuditLogRead)
def get_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single audit log entry by ID."""
    entry = get_audit_log(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    return entry
