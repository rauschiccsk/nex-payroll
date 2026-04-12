"""Tenant API router — CRUD endpoints.

Prefix: /api/v1/tenants (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.tenant import (
    TenantCreate,
    TenantRead,
    TenantUpdate,
)
from app.services import tenant_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tenants"])


# ---------------------------------------------------------------------------
# Error-mapping helper (DRY — shared across create/update/delete)
# ---------------------------------------------------------------------------


def _raise_for_value_error(exc: ValueError) -> None:
    """Map *ValueError* message to the appropriate HTTP status code.

    Pattern (per Router Generation Checklist):
      "not found"                          → 404
      "duplicate" / "conflict" / "already exists" → 409
      "invalid" / "constraint" / "foreign key"    → 422
      anything else                        → 409 (business-rule violation)
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


@router.get("", response_model=PaginatedResponse[TenantRead])
def list_tenants_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of tenants with optional filters."""
    items = tenant_service.list_tenants(db, skip=skip, limit=limit, is_active=is_active)
    total = tenant_service.count_tenants(db, is_active=is_active)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantRead)
def get_tenant_endpoint(
    tenant_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single tenant by ID."""
    tenant = tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("", response_model=TenantRead, status_code=201)
def create_tenant_endpoint(
    payload: TenantCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new tenant."""
    try:
        tenant = tenant_service.create_tenant(db, payload)
        db.commit()
    except ValueError as exc:
        _raise_for_value_error(exc)
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Tenant with ico='{payload.ico}' already exists",
        ) from None
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}", response_model=TenantRead)
def update_tenant_endpoint(
    tenant_id: UUID,
    payload: TenantUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing tenant (partial)."""
    try:
        tenant = tenant_service.update_tenant(db, tenant_id, payload)
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        db.commit()
        db.refresh(tenant)
    except HTTPException:
        raise
    except ValueError as exc:
        _raise_for_value_error(exc)
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tenant with duplicate ico already exists",
        ) from None
    return tenant


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant_endpoint(
    tenant_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a tenant by ID."""
    try:
        deleted = tenant_service.delete_tenant(db, tenant_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    except (IntegrityError, ProgrammingError):
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete tenant: dependent records exist",
        ) from None
    if not deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    db.commit()
