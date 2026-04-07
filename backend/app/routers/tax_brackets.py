"""TaxBracket API router — CRUD endpoints.

Prefix: /api/v1/tax-brackets (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.tax_bracket import (
    TaxBracketCreate,
    TaxBracketRead,
    TaxBracketUpdate,
)
from app.services.tax_bracket import (
    count_tax_brackets,
    create_tax_bracket,
    delete_tax_bracket,
    get_tax_bracket,
    list_tax_brackets,
    update_tax_bracket,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tax Brackets"])


@router.get("", response_model=PaginatedResponse[TaxBracketRead])
def list_brackets(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of tax brackets."""
    items = list_tax_brackets(db, skip=skip, limit=limit)
    total = count_tax_brackets(db)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{bracket_id}", response_model=TaxBracketRead)
def get_bracket(
    bracket_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single tax bracket by ID."""
    bracket = get_tax_bracket(db, bracket_id)
    if bracket is None:
        raise HTTPException(status_code=404, detail="Tax bracket not found")
    return bracket


@router.post("", response_model=TaxBracketRead, status_code=201)
def create_bracket(
    payload: TaxBracketCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new tax bracket."""
    try:
        bracket = create_tax_bracket(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(bracket)
    return bracket


@router.patch("/{bracket_id}", response_model=TaxBracketRead)
def update_bracket(
    bracket_id: UUID,
    payload: TaxBracketUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing tax bracket."""
    try:
        bracket = update_tax_bracket(db, bracket_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if bracket is None:
        raise HTTPException(status_code=404, detail="Tax bracket not found")
    db.commit()
    db.refresh(bracket)
    return bracket


@router.delete("/{bracket_id}", status_code=204)
def delete_bracket(
    bracket_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a tax bracket by ID."""
    deleted = delete_tax_bracket(db, bracket_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tax bracket not found")
    db.commit()
