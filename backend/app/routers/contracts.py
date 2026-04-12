"""Contract API router — CRUD endpoints.

Prefix: /api/v1/contracts (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.contract import (
    ContractCreate,
    ContractRead,
    ContractUpdate,
)
from app.schemas.pagination import PaginatedResponse
from app.services import contract as contract_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Contracts"])


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


# ---------------------------------------------------------------------------
# GET  /contracts          — paginated list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[ContractRead])
def list_contracts_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    is_current: bool | None = Query(  # noqa: B008
        None, description="Filter by current status (true/false)"
    ),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of contracts."""
    items = contract_service.list_contracts(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        is_current=is_current,
        skip=skip,
        limit=limit,
    )
    total = contract_service.count_contracts(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        is_current=is_current,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /contracts/{id}     — detail
# ---------------------------------------------------------------------------


@router.get("/{contract_id}", response_model=ContractRead)
def get_contract_endpoint(
    contract_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single contract by ID."""
    contract = contract_service.get_contract(db, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


# ---------------------------------------------------------------------------
# POST /contracts          — create
# ---------------------------------------------------------------------------


@router.post("", response_model=ContractRead, status_code=201)
def create_contract_endpoint(
    payload: ContractCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new contract."""
    try:
        contract = contract_service.create_contract(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(contract)
    return contract


# ---------------------------------------------------------------------------
# PATCH /contracts/{id}    — partial update
# ---------------------------------------------------------------------------


@router.patch("/{contract_id}", response_model=ContractRead)
def update_contract_endpoint(
    contract_id: UUID,
    payload: ContractUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing contract (partial — only supplied fields change)."""
    try:
        contract = contract_service.update_contract(db, contract_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.commit()
    db.refresh(contract)
    return contract


# ---------------------------------------------------------------------------
# DELETE /contracts/{id}   — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{contract_id}", status_code=204)
def delete_contract_endpoint(
    contract_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a contract by ID.

    Fails with 409 if the contract has dependent payroll records.
    """
    try:
        deleted = contract_service.delete_contract(db, contract_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.commit()
