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
from app.services.contract import (
    count_contracts,
    create_contract,
    delete_contract,
    get_contract,
    list_contracts,
    update_contract,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Contracts"])


@router.get("", response_model=PaginatedResponse[ContractRead])
def list_contracts_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    employee_id: UUID | None = Query(None, description="Filter by employee"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of contracts."""
    items = list_contracts(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        skip=skip,
        limit=limit,
    )
    total = count_contracts(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
    )
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{contract_id}", response_model=ContractRead)
def get_contract_endpoint(
    contract_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single contract by ID."""
    contract = get_contract(db, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.post("", response_model=ContractRead, status_code=201)
def create_contract_endpoint(
    payload: ContractCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new contract."""
    try:
        contract = create_contract(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(contract)
    return contract


@router.put("/{contract_id}", response_model=ContractRead)
def update_contract_endpoint(
    contract_id: UUID,
    payload: ContractUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing contract."""
    try:
        contract = update_contract(db, contract_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/{contract_id}", status_code=204)
def delete_contract_endpoint(
    contract_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a contract by ID."""
    try:
        deleted = delete_contract(db, contract_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.commit()
