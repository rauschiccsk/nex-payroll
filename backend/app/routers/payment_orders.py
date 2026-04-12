"""PaymentOrder API router — CRUD endpoints.

Prefix: /api/v1/payment-orders (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.payment_order import (
    PaymentOrderCreate,
    PaymentOrderRead,
    PaymentOrderUpdate,
)
from app.services import payment_order as payment_order_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payment Orders"])


# ---------------------------------------------------------------------------
# Error-mapping helper (DRY — shared across create/update/delete)
# ---------------------------------------------------------------------------


def _raise_for_value_error(exc: ValueError) -> None:
    """Map *ValueError* message to the appropriate HTTP status code.

    Pattern (per Router Generation Checklist):
      "not found"                          -> 404
      "duplicate" / "conflict" / "already exists" -> 409
      "invalid" / "constraint" / "foreign key"    -> 422
      anything else                        -> 409 (business-rule violation)
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
# GET  /payment-orders              — paginated list
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[PaymentOrderRead])
def list_payment_orders_endpoint(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    tenant_id: UUID | None = Query(None, description="Filter by tenant"),  # noqa: B008
    payment_type: str | None = Query(None, description="Filter by payment type"),  # noqa: B008
    status: str | None = Query(None, description="Filter by status"),  # noqa: B008
    period_year: int | None = Query(None, ge=2000, le=2100, description="Filter by period year"),  # noqa: B008
    period_month: int | None = Query(None, ge=1, le=12, description="Filter by period month"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a paginated list of payment orders."""
    try:
        items = payment_order_service.list_payment_orders(
            db,
            tenant_id=tenant_id,
            payment_type=payment_type,
            status=status,
            period_year=period_year,
            period_month=period_month,
            skip=skip,
            limit=limit,
        )
        total = payment_order_service.count_payment_orders(
            db,
            tenant_id=tenant_id,
            payment_type=payment_type,
            status=status,
            period_year=period_year,
            period_month=period_month,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /payment-orders/{id}         — detail
# ---------------------------------------------------------------------------


@router.get("/{order_id}", response_model=PaymentOrderRead)
def get_payment_order_endpoint(
    order_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single payment order by ID."""
    order = payment_order_service.get_payment_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Payment order not found")
    return order


# ---------------------------------------------------------------------------
# POST /payment-orders              — create
# ---------------------------------------------------------------------------


@router.post("", response_model=PaymentOrderRead, status_code=201)
def create_payment_order_endpoint(
    payload: PaymentOrderCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new payment order record."""
    try:
        order = payment_order_service.create_payment_order(db, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# PATCH /payment-orders/{id}        — partial update
# ---------------------------------------------------------------------------


@router.patch("/{order_id}", response_model=PaymentOrderRead)
def update_payment_order_endpoint(
    order_id: UUID,
    payload: PaymentOrderUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing payment order record (partial — only supplied fields change)."""
    try:
        order = payment_order_service.update_payment_order(db, order_id, payload)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# DELETE /payment-orders/{id}       — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{order_id}", status_code=204)
def delete_payment_order_endpoint(
    order_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a payment order by ID."""
    try:
        payment_order_service.delete_payment_order(db, order_id)
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
