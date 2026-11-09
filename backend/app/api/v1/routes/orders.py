"""Order management and transaction ledger."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.deps import AuthContext, SessionDep, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import OrderStatus
from app.models.payment import PaymentInvoice
from app.schemas.common import MessageResponse, Page
from app.schemas.order import (
    OrderNoteUpdate,
    OrderOut,
    OrderStatusUpdate,
    TransactionOut,
)
from app.services import (
    audit_service,
    delivery_service,
    order_service,
    payments,
)

router = APIRouter(tags=["orders"])

OrderCtx = Annotated[AuthContext, Depends(require_permission("orders.manage"))]
TransactionCtx = Annotated[
    AuthContext, Depends(require_permission("transactions.view"))
]


@router.get("/orders", response_model=Page[OrderOut])
async def list_orders(
    ctx: OrderCtx,
    session: SessionDep,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    product_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[OrderOut]:
    items, total = await order_service.list_orders(
        session,
        status=status,
        customer_id=customer_id,
        product_id=product_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return Page[OrderOut].build(items, total, page, page_size)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int, ctx: OrderCtx, session: SessionDep
) -> OrderOut:
    order = await order_service.get_order(session, order_id)
    return order_service.order_to_out(order)


@router.patch("/orders/{order_id}/note", response_model=OrderOut)
async def update_note(
    order_id: int, payload: OrderNoteUpdate, ctx: OrderCtx, session: SessionDep
) -> OrderOut:
    order = await order_service.get_order(session, order_id)
    order.admin_note = payload.admin_note
    await session.flush()
    await audit_service.record(
        session, ctx.admin, "order.note", "order", order.id,
        f"Catatan pesanan {order.order_code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return order_service.order_to_out(order)


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
async def update_status(
    order_id: int, payload: OrderStatusUpdate, ctx: OrderCtx, session: SessionDep
) -> OrderOut:
    order = await order_service.get_order(session, order_id)
    before = order.status
    await order_service.set_order_status(session, order, payload.status, payload.note)
    await audit_service.record(
        session, ctx.admin, "order.status", "order", order.id,
        f"Status {order.order_code}: {before} -> {order.status}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: int, ctx: OrderCtx, session: SessionDep
) -> OrderOut:
    order = await order_service.get_order(session, order_id)
    await order_service.cancel_order(session, order, reason="Dibatalkan oleh admin")
    await audit_service.record(
        session, ctx.admin, "order.cancel", "order", order.id,
        f"Membatalkan pesanan {order.order_code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/mark-paid", response_model=OrderOut)
async def mark_paid(
    order_id: int, ctx: OrderCtx, session: SessionDep
) -> OrderOut:
    """Manual settlement for an order paid outside the gateway."""
    order = await order_service.get_order(session, order_id)
    if order.status in order_service.PAID_STATUSES:
        raise ConflictError("Pesanan sudah dibayar")
    transitioned = await order_service.mark_order_paid(session, order)
    if not transitioned:
        raise ConflictError("Pesanan tidak dapat ditandai dibayar")
    await delivery_service.fulfill_order(session, order)
    invoice = order.active_invoice
    if invoice is not None:
        invoice.status = "PAID"
        invoice.paid_at = order_service.utcnow()
    await audit_service.record(
        session, ctx.admin, "order.mark_paid", "order", order.id,
        f"Menandai pesanan {order.order_code} sebagai dibayar", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/invoice/refresh", response_model=OrderOut)
async def refresh_invoice(
    order_id: int, ctx: OrderCtx, session: SessionDep
) -> OrderOut:
    order = await order_service.get_order(session, order_id)
    invoice = order.active_invoice
    if invoice is None:
        raise NotFoundError("Invoice tidak ditemukan")
    await payments.refresh_invoice(session, invoice)
    await audit_service.record(
        session, ctx.admin, "order.invoice_refresh", "order", order.id,
        f"Memeriksa ulang invoice {order.order_code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    await session.refresh(order)
    return order_service.order_to_out(order)


@router.post("/orders/{order_id}/invoice/recreate", response_model=OrderOut)
async def recreate_invoice(
    order_id: int, ctx: OrderCtx, session: SessionDep
) -> OrderOut:
    order = await order_service.get_order(session, order_id)
    if order.status != OrderStatus.PENDING_PAYMENT.value:
        raise ConflictError("Invoice hanya dapat dibuat ulang untuk pesanan yang belum dibayar")
    for invoice in order.invoices:
        if invoice.status in ("PENDING", "CONFIRMING"):
            invoice.status = "CANCELLED"
    await session.flush()
    await payments.create_invoice(session, order, order.customer)
    await audit_service.record(
        session, ctx.admin, "order.invoice_recreate", "order", order.id,
        f"Membuat ulang invoice {order.order_code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    await session.refresh(order)
    return order_service.order_to_out(order)


@router.get("/transactions", response_model=Page[TransactionOut])
async def list_transactions(
    ctx: TransactionCtx,
    session: SessionDep,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[TransactionOut]:
    items, total = await order_service.list_transactions(
        session, status=status, search=search, page=page, page_size=page_size
    )
    return Page[TransactionOut].build(items, total, page, page_size)
