"""Payment invoices, gateway webhooks and provider diagnostics."""
from datetime import datetime, timezone
from typing import Annotated, List, Optional

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import AuthContext, SessionDep, require_permission
from app.core.exceptions import NotFoundError
from app.models.enums import PaymentStatus
from app.models.order import Order
from app.models.payment import PaymentInvoice, WebhookEvent
from app.schemas.common import Page
from app.schemas.payment import (
    ManualPaymentRequest,
    PaymentInvoiceOut,
    ProviderCheckResponse,
    ProviderStatus,
    WebhookAck,
    WebhookEventOut,
)
from app.services import audit_service, delivery_service, order_service, payments

router = APIRouter(prefix="/payments", tags=["payments"])

PaymentCtx = Annotated[AuthContext, Depends(require_permission("payments.view"))]


def _invoice_out(invoice: PaymentInvoice, order_code: Optional[str] = None) -> PaymentInvoiceOut:
    return PaymentInvoiceOut(
        id=invoice.id,
        order_id=invoice.order_id,
        order_code=order_code,
        provider=invoice.provider,
        provider_invoice_id=invoice.provider_invoice_id,
        provider_order_ref=invoice.provider_order_ref,
        amount=float(invoice.amount),
        paid_amount=float(invoice.paid_amount) if invoice.paid_amount else None,
        currency=invoice.currency,
        network=invoice.network,
        pay_address=invoice.pay_address,
        pay_amount=float(invoice.pay_amount) if invoice.pay_amount else None,
        payer_currency=invoice.payer_currency,
        qr_code_url=invoice.qr_code_url,
        payment_url=invoice.payment_url,
        status=invoice.status,
        provider_status=invoice.provider_status,
        tx_hash=invoice.tx_hash,
        confirmations=invoice.confirmations,
        is_manual=invoice.is_manual,
        expires_at=invoice.expires_at,
        paid_at=invoice.paid_at,
        created_at=invoice.created_at,
    )


@router.get("/invoices", response_model=Page[PaymentInvoiceOut])
async def list_invoices(
    ctx: PaymentCtx,
    session: SessionDep,
    status: Optional[str] = None,
    provider: Optional[str] = None,
    order_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[PaymentInvoiceOut]:
    conditions = []
    if status:
        conditions.append(PaymentInvoice.status == status)
    if provider:
        conditions.append(PaymentInvoice.provider == provider)
    if order_id:
        conditions.append(PaymentInvoice.order_id == order_id)

    count_query = select(func.count(PaymentInvoice.id))
    query = select(PaymentInvoice)
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.order_by(PaymentInvoice.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for invoice in result.scalars().all():
        order = await session.get(Order, invoice.order_id)
        items.append(_invoice_out(invoice, order.order_code if order else None))
    return Page[PaymentInvoiceOut].build(items, total, page, page_size)


@router.get("/invoices/{invoice_id}", response_model=PaymentInvoiceOut)
async def get_invoice(
    invoice_id: int, ctx: PaymentCtx, session: SessionDep
) -> PaymentInvoiceOut:
    invoice = await session.get(PaymentInvoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice tidak ditemukan")
    order = await session.get(Order, invoice.order_id)
    return _invoice_out(invoice, order.order_code if order else None)


@router.post("/invoices/{invoice_id}/check", response_model=PaymentInvoiceOut)
async def check_invoice(
    invoice_id: int, ctx: PaymentCtx, session: SessionDep
) -> PaymentInvoiceOut:
    invoice = await session.get(PaymentInvoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice tidak ditemukan")
    await payments.refresh_invoice(session, invoice)
    order = await session.get(Order, invoice.order_id)
    await audit_service.record(
        session, ctx.admin, "payment.check", "invoice", invoice.id,
        f"Memeriksa status invoice {invoice.provider_invoice_id}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return _invoice_out(invoice, order.order_code if order else None)


@router.post("/invoices/{invoice_id}/manual", response_model=PaymentInvoiceOut)
async def manual_settlement(
    invoice_id: int,
    payload: ManualPaymentRequest,
    ctx: PaymentCtx,
    session: SessionDep,
) -> PaymentInvoiceOut:
    """Settle an invoice manually (bank transfer style crypto payment)."""
    invoice = await session.get(PaymentInvoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice tidak ditemukan")
    if invoice.status in (PaymentStatus.PAID.value, PaymentStatus.OVERPAID.value):
        order = await session.get(Order, invoice.order_id)
        return _invoice_out(invoice, order.order_code if order else None)

    order = await session.get(Order, invoice.order_id)
    if order is None:
        raise NotFoundError("Pesanan tidak ditemukan")

    invoice.status = PaymentStatus.PAID.value
    invoice.provider_status = "manual"
    invoice.is_manual = True
    invoice.paid_amount = payload.paid_amount or float(invoice.amount)
    invoice.tx_hash = payload.tx_hash or invoice.tx_hash
    invoice.paid_at = datetime.now(timezone.utc)
    await session.flush()

    await order_service.mark_order_paid(session, order, payload.paid_amount)
    await delivery_service.fulfill_order(session, order)
    await audit_service.record(
        session, ctx.admin, "payment.manual", "invoice", invoice.id,
        f"Settel manual invoice {invoice.provider_invoice_id}", details=payload.model_dump(),
        ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return _invoice_out(invoice, order.order_code)


@router.get("/webhook-events", response_model=Page[WebhookEventOut])
async def list_webhook_events(
    ctx: PaymentCtx,
    session: SessionDep,
    processed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
) -> Page[WebhookEventOut]:
    conditions = []
    if processed is not None:
        conditions.append(WebhookEvent.processed.is_(processed))
    count_query = select(func.count(WebhookEvent.id))
    query = select(WebhookEvent)
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)
    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.order_by(WebhookEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page[WebhookEventOut].build(
        [WebhookEventOut.model_validate(row) for row in result.scalars().all()],
        total,
        page,
        page_size,
    )


@router.post("/webhook/{provider_name}", response_model=WebhookAck)
async def payment_webhook(
    provider_name: str, request: Request, session: SessionDep
) -> WebhookAck:
    """Public gateway callback. Authenticity is enforced by signature."""
    raw_body = await request.body()
    status = await payments.process_webhook(
        session, provider_name, dict(request.headers), raw_body
    )
    return WebhookAck(status=status)


@router.get("/provider", response_model=ProviderStatus)
async def provider_status(ctx: PaymentCtx) -> ProviderStatus:
    provider = payments.get_provider()
    return ProviderStatus(
        provider=provider.name,
        configured=provider.configured,
        merchant_uuid_set=bool(settings.cryptomus_merchant_uuid),
        api_key_set=bool(settings.cryptomus_api_key),
        network=settings.cryptomus_network,
        currency=settings.payment_currency,
        webhook_url=f"{settings.webhook_base_url.rstrip('/')}/api/v1/payments/webhook/{provider.name}",
        supported_networks=["bep20"] if provider.configured else [],
        notes=(
            "Konfirmasi ketersediaan USDT BEP20 pada akun merchant Cryptomus "
            "sebelum menerima pembayaran nyata."
        ),
    )


@router.post("/provider-check", response_model=ProviderCheckResponse)
async def provider_check(ctx: PaymentCtx) -> ProviderCheckResponse:
    """Ping the gateway API and report whether BEP20 appears configured."""
    provider = payments.get_provider()
    if not provider.configured:
        return ProviderCheckResponse(
            provider=provider.name,
            reachable=False,
            usdt_bep20_supported=False,
            detail="Kredensial merchant belum diisi",
        )
    reachable = False
    detail = ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{settings.cryptomus_api_url.rstrip('/')}/payment")
            reachable = response.status_code < 500
            detail = f"Cryptomus merespons HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        detail = f"Tidak dapat menghubungi Cryptomus: {exc}"
    return ProviderCheckResponse(
        provider=provider.name,
        reachable=reachable,
        usdt_bep20_supported=reachable
        and settings.cryptomus_network.lower() == "bep20",
        detail=detail
        + ". Pastikan USDT BEP20 aktif di dashboard merchant Cryptomus Anda.",
    )


@router.get("/mock/{order_code}/pay", response_class=HTMLResponse, include_in_schema=False)
async def mock_pay(order_code: str, session: SessionDep) -> HTMLResponse:
    if settings.payment_provider != "mock" or settings.is_production:
        return HTMLResponse("<h3>Simulasi pembayaran tidak tersedia</h3>", status_code=404)
    try:
        await payments.simulate_mock_payment(session, order_code, "paid")
    except Exception as exc:
        return HTMLResponse(f"<h3>Gagal: {exc}</h3>", status_code=400)
    return HTMLResponse(
        f"<h3>Pembayaran mock untuk {order_code} berhasil.</h3>"
        "<p>Kembali ke Telegram, produk akan dikirim otomatis.</p>"
    )
