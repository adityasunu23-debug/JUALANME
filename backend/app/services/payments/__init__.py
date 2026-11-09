"""Payment gateway factory, invoice creation and webhook processing."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    NotFoundError,
    PaymentError,
    ProviderError,
    ValidationError,
    WebhookSignatureError,
)
from app.core.security import canonical_json
from app.models.customer import Customer
from app.models.enums import OrderStatus, PaymentStatus
from app.models.order import Order
from app.models.payment import PaymentInvoice, WebhookEvent
from app.models.setting import Setting
from app.services.payments.base import (
    PAID_STATUSES,
    PaymentProvider,
    ProviderInvoice,
    normalize_status,
)
from app.services.payments.cryptomus import CryptomusError, CryptomusProvider
from app.services.payments.mock import MockProvider

logger = logging.getLogger(__name__)


def resolve_provider_name(name: Optional[str] = None) -> str:
    return (name or settings.payment_provider or "cryptomus").strip().lower()


def get_provider(name: Optional[str] = None) -> PaymentProvider:
    resolved = resolve_provider_name(name)
    if resolved == "mock":
        return MockProvider()
    if resolved == "cryptomus":
        return CryptomusProvider()
    raise NotFoundError(f"Payment provider tidak dikenal: {resolved}")


async def _require_signature(session: AsyncSession) -> bool:
    result = await session.execute(
        select(Setting.value).where(Setting.key == "security.webhook_require_signature")
    )
    row = result.scalar_one_or_none()
    if row is None:
        return True
    return str(row).strip().lower() in ("1", "true", "yes", "on")


async def create_invoice(
    session: AsyncSession, order: Order, customer: Customer
) -> PaymentInvoice:
    """Create a gateway invoice for an order and persist it."""
    provider = get_provider()
    if not provider.configured:
        raise ProviderError(
            "Payment gateway belum dikonfigurasi. Isi kredensial Cryptomus di Settings."
        )

    try:
        data = await provider.create_invoice(order, customer)
    except CryptomusError as exc:
        raise ProviderError(str(exc)) from exc

    expires_at = data.expires_at or (
        datetime.now(timezone.utc)
        + timedelta(minutes=settings.invoice_lifetime_minutes)
    )
    invoice = PaymentInvoice(
        order_id=order.id,
        provider=provider.name,
        provider_invoice_id=data.provider_invoice_id,
        provider_order_ref=order.order_code,
        amount=float(order.total_amount),
        paid_amount=data.paid_amount,
        currency=settings.payment_currency,
        network=settings.cryptomus_network,
        pay_address=data.pay_address,
        pay_amount=data.pay_amount,
        payer_currency=data.payer_currency,
        qr_code_url=data.qr_code_url,
        payment_url=data.payment_url,
        status=data.status or PaymentStatus.PENDING.value,
        provider_status=data.provider_status,
        confirmations=data.confirmations,
        expires_at=expires_at,
        raw_response=data.raw or None,
    )
    session.add(invoice)
    await session.flush()
    return invoice


async def refresh_invoice(
    session: AsyncSession, invoice: PaymentInvoice
) -> PaymentInvoice:
    """Ask the gateway for the latest invoice state and apply it."""
    if not invoice.provider_invoice_id:
        return invoice
    provider = get_provider(invoice.provider)
    try:
        data = await provider.refresh_status(invoice.provider_invoice_id)
    except CryptomusError as exc:
        logger.warning("Invoice refresh failed for %s: %s", invoice.id, exc)
        invoice.last_checked_at = datetime.now(timezone.utc)
        return invoice

    invoice.last_checked_at = datetime.now(timezone.utc)
    if data.status:
        await apply_provider_update(session, invoice, data)
    return invoice


async def apply_provider_update(
    session: AsyncSession, invoice: PaymentInvoice, data: ProviderInvoice
) -> bool:
    """Merge gateway state into the invoice and settle the order once.

    Returns True when the invoice moved into a paid state for the first time.
    Never delivers twice: the order transition is guarded by a conditional
    UPDATE on its current status.
    """
    if invoice.status in PAID_STATUSES:
        return False

    raw = data.raw or {}
    actual_network = str(raw.get("network") or "").strip().lower()
    if actual_network and actual_network != settings.cryptomus_network.lower():
        invoice.status = PaymentStatus.FAILED.value
        invoice.provider_status = f"network_mismatch:{actual_network}"
        invoice.raw_response = raw or invoice.raw_response
        invoice.paid_at = datetime.now(timezone.utc)
        await session.flush()
        return False

    actual_currency = str(raw.get("currency") or "").strip().upper()
    if actual_currency and actual_currency != settings.payment_currency.upper():
        invoice.status = PaymentStatus.FAILED.value
        invoice.provider_status = f"currency_mismatch:{actual_currency}"
        invoice.raw_response = raw or invoice.raw_response
        await session.flush()
        return False

    for attr in ("pay_address", "pay_amount", "payer_currency", "payment_url"):
        value = getattr(data, attr, None)
        if value is not None:
            setattr(invoice, attr, value)
    if data.paid_amount is not None:
        invoice.paid_amount = data.paid_amount
    if data.tx_hash:
        invoice.tx_hash = data.tx_hash
    if data.confirmations:
        invoice.confirmations = data.confirmations
    if data.provider_status:
        invoice.provider_status = data.provider_status
    if data.status:
        invoice.status = data.status
    if raw:
        invoice.raw_response = raw

    status = invoice.status
    paid_now = False
    if status in PAID_STATUSES:
        invoice.paid_at = invoice.paid_at or datetime.now(timezone.utc)
        await session.flush()
        paid_now = await _settle_paid(session, invoice)
    elif status == PaymentStatus.UNDERPAID.value:
        invoice.order.admin_note = (
            "Underpaid: diterima "
            f"{float(invoice.paid_amount or 0):.2f} dari {float(invoice.amount):.2f}"
        )
        await session.flush()
    elif status in (
        PaymentStatus.FAILED.value,
        PaymentStatus.CANCELLED.value,
        PaymentStatus.EXPIRED.value,
    ):
        await _fail_order(session, invoice, status)

    return paid_now


async def _settle_paid(session: AsyncSession, invoice: PaymentInvoice) -> bool:
    from app.services import delivery_service, order_service

    order_result = await session.execute(
        select(Order).where(Order.id == invoice.order_id)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        return False

    transitioned = await order_service.mark_order_paid(
        session, order, paid_amount=invoice.paid_amount
    )
    if not transitioned:
        return False

    try:
        await delivery_service.fulfill_order(session, order)
    except Exception as exc:  # delivery failure must not roll back the payment
        logger.exception("Automatic delivery failed for %s: %s", order.order_code, exc)
        order.admin_note = f"Pengiriman gagal: {exc}"[:500]
    await session.flush()
    return True


async def _fail_order(
    session: AsyncSession, invoice: PaymentInvoice, status: str
) -> None:
    from app.services import order_service

    order_result = await session.execute(
        select(Order).where(Order.id == invoice.order_id)
    )
    order = order_result.scalar_one_or_none()
    if order is None or order.is_paid:
        return
    if order.status in (
        OrderStatus.CANCELLED.value,
        OrderStatus.EXPIRED.value,
        OrderStatus.FAILED.value,
    ):
        return
    await order_service.mark_order_failed(session, order, reason=status)


async def process_webhook(
    session: AsyncSession,
    provider_name: str,
    headers: Mapping[str, str],
    raw_body: bytes,
) -> str:
    """Validate, deduplicate and apply a gateway webhook. Returns a short status."""
    provider = get_provider(provider_name)
    try:
        payload: Dict[str, Any] = json.loads(raw_body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValidationError("Payload webhook bukan JSON yang valid") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Payload webhook harus berupa objek JSON")

    payload_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    existing = await session.execute(
        select(WebhookEvent.id).where(WebhookEvent.payload_hash == payload_hash)
    )
    if existing.scalar_one_or_none() is not None:
        return "duplicate"

    signature_valid = provider.verify_webhook(headers, payload, raw_body)
    required = await _require_signature(session)

    order_code = provider.webhook_order_ref(payload)
    invoice_id = provider.webhook_invoice_id(payload)
    event = WebhookEvent(
        provider=provider.name,
        event_type=str(payload.get("status") or payload.get("payment_status") or "")[
            :32
        ]
        or None,
        payload_hash=payload_hash,
        signature_valid=signature_valid,
        processed=False,
        order_code=order_code,
        provider_invoice_id=invoice_id,
        payload=json.dumps(payload, default=str)[:8000],
    )
    session.add(event)
    try:
        await session.flush()
    except Exception:
        await session.rollback()
        return "duplicate"

    if required and not signature_valid:
        event.error = "Signature webhook tidak valid"
        await session.commit()
        raise WebhookSignatureError("Signature webhook tidak valid")

    invoice = await _find_invoice(session, invoice_id, order_code)
    if invoice is None:
        event.error = "Invoice tidak ditemukan"
        await session.commit()
        return "ignored"

    data = provider.provider_invoice(payload)
    if not data.provider_invoice_id:
        data.provider_invoice_id = invoice.provider_invoice_id
    try:
        await apply_provider_update(session, invoice, data)
        event.processed = True
    except PaymentError as exc:
        event.error = str(exc)[:1000]
    except Exception as exc:  # pragma: no cover - unexpected gateway data
        logger.exception("Webhook processing failed")
        event.error = str(exc)[:1000]
    await session.commit()
    return "ok" if event.processed else "ignored"


async def _find_invoice(
    session: AsyncSession,
    provider_invoice_id: Optional[str],
    order_code: Optional[str],
) -> Optional[PaymentInvoice]:
    if provider_invoice_id:
        result = await session.execute(
            select(PaymentInvoice).where(
                PaymentInvoice.provider_invoice_id == provider_invoice_id
            )
        )
        invoice = result.scalar_one_or_none()
        if invoice is not None:
            return invoice
    if order_code:
        result = await session.execute(
            select(PaymentInvoice)
            .join(Order, Order.id == PaymentInvoice.order_id)
            .where(Order.order_code == order_code)
            .order_by(PaymentInvoice.id.desc())
        )
        return result.scalars().first()
    return None


async def simulate_mock_payment(
    session: AsyncSession, order_code: str, status: str = "paid"
) -> PaymentInvoice:
    """Development helper: mark a mock invoice as paid without a gateway."""
    result = await session.execute(
        select(Order).where(Order.order_code == order_code)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Pesanan tidak ditemukan")
    invoice_result = await session.execute(
        select(PaymentInvoice)
        .where(PaymentInvoice.order_id == order.id)
        .order_by(PaymentInvoice.id.desc())
    )
    invoice = invoice_result.scalars().first()
    if invoice is None:
        raise NotFoundError("Invoice tidak ditemukan")
    if invoice.provider != "mock":
        raise ValidationError("Simulasi hanya tersedia untuk provider mock")

    data = ProviderInvoice(
        provider_invoice_id=invoice.provider_invoice_id,
        status=normalize_status(status, float(invoice.amount), float(invoice.amount)),
        provider_status=status,
        paid_amount=float(invoice.amount),
        pay_address=invoice.pay_address,
        tx_hash="0x" + hashlib.sha256(order.order_code.encode()).hexdigest(),
        raw={"network": settings.cryptomus_network, "currency": settings.payment_currency},
    )
    await apply_provider_update(session, invoice, data)
    await session.commit()
    return invoice
