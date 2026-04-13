"""PaymentOrder API router — CRUD + SEPA XML endpoints.

Prefix: /api/v1/payments (set in main.py via include_router)
All endpoints use def (NEVER async def) per DESIGN.md.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.payment_order import (
    PaymentOrderCreate,
    PaymentOrderRead,
    PaymentOrderStatusUpdate,
    PaymentOrderUpdate,
)
from app.services import payment_order as payment_order_service
from app.services import sepa_generator

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


# ---------------------------------------------------------------------------
# PUT  /payments/{id}/status        — update status only
# ---------------------------------------------------------------------------


@router.put("/{order_id}/status", response_model=PaymentOrderRead)
def update_payment_order_status_endpoint(
    order_id: UUID,
    payload: PaymentOrderStatusUpdate,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update the status of a payment order (pending → exported → paid)."""
    try:
        order = payment_order_service.update_payment_order(
            db,
            order_id,
            PaymentOrderUpdate(status=payload.status),
        )
    except ValueError as exc:
        _raise_for_value_error(exc)
    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------------------
# GET  /payments/{year}/{month}     — list orders for a specific period
# ---------------------------------------------------------------------------


@router.get("/{year}/{month}", response_model=PaginatedResponse[PaymentOrderRead])
def list_payment_orders_by_period_endpoint(
    year: int,
    month: int,
    tenant_id: UUID = Query(..., description="Filter by tenant"),  # noqa: B008
    payment_type: str | None = Query(None, description="Filter by payment type"),  # noqa: B008
    status: str | None = Query(None, description="Filter by status"),  # noqa: B008
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return payment orders for a specific year/month period."""
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="year must be between 2000 and 2100")

    try:
        items = payment_order_service.list_payment_orders(
            db,
            tenant_id=tenant_id,
            payment_type=payment_type,
            status=status,
            period_year=year,
            period_month=month,
            skip=skip,
            limit=limit,
        )
        total = payment_order_service.count_payment_orders(
            db,
            tenant_id=tenant_id,
            payment_type=payment_type,
            status=status,
            period_year=year,
            period_month=month,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# GET  /payments/{year}/{month}/sepa-xml  — download SEPA XML
# ---------------------------------------------------------------------------


@router.get("/{year}/{month}/sepa-xml")
def download_sepa_xml_endpoint(
    year: int,
    month: int,
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Download SEPA XML (pain.001.001.03) for all pending/exported orders.

    Returns XML without changing order status (preview mode).
    To export and mark as 'exported', use POST /{year}/{month}/sepa-xml.
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="year must be between 2000 and 2100")

    try:
        xml_bytes = sepa_generator.generate_sepa_xml_preview(
            db,
            tenant_id=tenant_id,
            period_year=year,
            period_month=month,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)

    filename = f"SEPA-{year}-{month:02d}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /payments/{year}/{month}/sepa-xml  — generate & export SEPA XML
# ---------------------------------------------------------------------------


@router.post("/{year}/{month}/sepa-xml")
def generate_sepa_xml_endpoint(
    year: int,
    month: int,
    tenant_id: UUID = Query(..., description="Tenant ID"),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Generate SEPA XML and mark all pending orders as 'exported'.

    Returns the XML document.  Orders are transitioned from
    'pending' → 'exported' atomically.
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=422, detail="year must be between 2000 and 2100")

    try:
        xml_bytes = sepa_generator.generate_sepa_xml(
            db,
            tenant_id=tenant_id,
            period_year=year,
            period_month=month,
        )
    except ValueError as exc:
        _raise_for_value_error(exc)

    db.commit()

    filename = f"SEPA-{year}-{month:02d}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
