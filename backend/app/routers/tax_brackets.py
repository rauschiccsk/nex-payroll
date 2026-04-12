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
from app.services import tax_bracket as tax_bracket_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tax Brackets"])


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
# GET  /tax-brackets          — paginated list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[TaxBracketRead])
def list_brackets(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of tax brackets."""
    items = tax_bracket_service.list_tax_brackets(db, skip=skip, limit=limit)
    total = tax_bracket_service.count_tax_brackets(db)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /tax-brackets/{id}     — detail
# ---------------------------------------------------------------------------


@router.get("/{bracket_id}", response_model=TaxBracketRead)
def get_bracket(
    bracket_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single tax bracket by ID."""
    bracket = tax_bracket_service.get_tax_bracket(db, bracket_id)
    if bracket is None:
        raise HTTPException(status_code=404, detail="Tax bracket not found")
    return bracket


# ---------------------------------------------------------------------------
# POST /tax-brackets          — create
# ---------------------------------------------------------------------------


@router.post("", response_model=TaxBracketRead, status_code=201)
def create_bracket(
    payload: TaxBracketCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new tax bracket."""
    try:
        bracket = tax_bracket_service.create_tax_bracket(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(bracket)
    return bracket


# ---------------------------------------------------------------------------
# PATCH /tax-brackets/{id}    — partial update
# ---------------------------------------------------------------------------


@router.patch("/{bracket_id}", response_model=TaxBracketRead)
def update_bracket(
    bracket_id: UUID,
    payload: TaxBracketUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing tax bracket."""
    try:
        bracket = tax_bracket_service.update_tax_bracket(db, bracket_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    if bracket is None:
        raise HTTPException(status_code=404, detail="Tax bracket not found")
    db.commit()
    db.refresh(bracket)
    return bracket


# ---------------------------------------------------------------------------
# DELETE /tax-brackets/{id}   — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{bracket_id}", status_code=204)
def delete_bracket(
    bracket_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a tax bracket by ID."""
    deleted = tax_bracket_service.delete_tax_bracket(db, bracket_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tax bracket not found")
    db.commit()
