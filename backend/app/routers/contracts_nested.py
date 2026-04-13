"""Nested contract routes under /employees/{employee_id}/contracts.

DESIGN.md §6.5 — contracts are sub-resources of employees.
Prefix /api/v1 is set in main.py; this router adds
/employees/{employee_id}/contracts.

All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.contract import ContractCreate, ContractRead
from app.schemas.pagination import PaginatedResponse
from app.services import contract as contract_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/employees/{employee_id}/contracts",
    tags=["Contracts"],
)


@router.get("", response_model=PaginatedResponse[ContractRead])
def list_contracts_by_employee(
    employee_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedResponse[ContractRead]:
    """Return paginated contracts for a specific employee."""
    items = contract_service.list_contracts(db, employee_id=employee_id, skip=skip, limit=limit)
    total = contract_service.count_contracts(db, employee_id=employee_id)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=ContractRead, status_code=201)
def create_contract_for_employee(
    employee_id: UUID,
    data: ContractCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> ContractRead:
    """Create a new contract for the given employee.

    The employee_id path param overrides any employee_id in the request body.
    """
    # Build payload with employee_id from path
    payload_data = data.model_dump()
    payload_data["employee_id"] = employee_id
    merged = ContractCreate(**payload_data)

    try:
        contract = contract_service.create_contract(db, merged)
    except ValueError as exc:
        msg = str(exc).lower()
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if any(kw in msg for kw in ("duplicate", "conflict", "already exists")):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(contract)
    return contract
