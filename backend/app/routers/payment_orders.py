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
from app.services.payment_order import (
    count_payment_orders,
    create_payment_order,
    delete_payment_order,
    get_payment_order,
    list_payment_orders,
    update_payment_order,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payment Orders"])


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
        items = list_payment_orders(
            db,
            tenant_id=tenant_id,
            payment_type=payment_type,
            status=status,
            period_year=period_year,
            period_month=period_month,
            skip=skip,
            limit=limit,
        )
        total = count_payment_orders(
            db,
            tenant_id=tenant_id,
            payment_type=payment_type,
            status=status,
            period_year=period_year,
            period_month=period_month,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=PaymentOrderRead)
def get_payment_order_endpoint(
    order_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return a single payment order by ID."""
    order = get_payment_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Payment order not found")
    return order


@router.post("", response_model=PaymentOrderRead, status_code=201)
def create_payment_order_endpoint(
    payload: PaymentOrderCreate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Create a new payment order record."""
    try:
        order = create_payment_order(db, payload)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=422, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=PaymentOrderRead)
def update_payment_order_endpoint(
    order_id: UUID,
    payload: PaymentOrderUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update an existing payment order record."""
    try:
        order = update_payment_order(db, order_id, payload)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=409, detail=msg) from exc
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=204)
def delete_payment_order_endpoint(
    order_id: UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Delete a payment order by ID."""
    try:
        delete_payment_order(db, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
