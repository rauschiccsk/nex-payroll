"""Tenant API router — CRUD endpoints.

Prefix: /api/v1/tenants (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.tenant import (
    TenantCreate,
    TenantRead,
    TenantUpdate,
)
from app.services.tenant import (
    count_tenants,
    create_tenant,
    delete_tenant,
    get_tenant,
    list_tenants,
    update_tenant,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tenants"])


@router.get("", response_model=PaginatedResponse[TenantRead])
def list_tenants_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of tenants."""
    items = list_tenants(db, skip=skip, limit=limit)
    total = count_tenants(db)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{tenant_id}", response_model=TenantRead)
def get_tenant_endpoint(
    tenant_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single tenant by ID."""
    tenant = get_tenant(db, tenant_id)
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
        tenant = create_tenant(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(tenant)
    return tenant


@router.put("/{tenant_id}", response_model=TenantRead)
def update_tenant_endpoint(
    tenant_id: UUID,
    payload: TenantUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing tenant."""
    try:
        tenant = update_tenant(db, tenant_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant_endpoint(
    tenant_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a tenant by ID."""
    deleted = delete_tenant(db, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    db.commit()
