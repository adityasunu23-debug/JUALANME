"""Order creation, payment state transitions and expiry handling."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    OutOfStock,
    ProductUnavailableError,
    ValidationError,
)
from app.models.catalog import Product
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.enums import (
    DeliveryStatus,
    DeliveryType,
    OrderStatus,
    PaymentStatus,
)
from app.models.order import Order
from app.models.payment import PaymentInvoice
from app.schemas.order import (
    DeliveryOut,
    InvoiceSummary,
    OrderOut,
    TransactionOut,
)
from app.services import (
    customer_service,
    stock_service,
    telegram_notify,
    voucher_service,
)

logger = logging.getLogger(__name__)

PAID_STATUSES = (
    OrderStatus.PAID.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.COMPLETED.value,
)
OPEN_STATUSES = (OrderStatus.PENDING_PAYMENT.value,)
FINAL_STATUSES = (
    OrderStatus.EXPIRED.value,
    OrderStatus.CANCELLED.value,
    OrderStatus.REFUNDED.value,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def generate_order_code() -> str:
    return "ORD-" + datetime.now(timezone.utc).strftime("%y%m%d") + "-" + secrets.token_hex(3).upper()


def summarize_invoice(invoice: PaymentInvoice) -> InvoiceSummary:
    return InvoiceSummary(
        id=invoice.id,
        provider=invoice.provider,
        provider_invoice_id=invoice.provider_invoice_id,
        amount=float(invoice.amount),
        paid_amount=float(invoice.paid_amount) if invoice.paid_amount else None,
        currency=invoice.currency,
        network=invoice.network,
        pay_address=invoice.pay_address,
        pay_amount=float(invoice.pay_amount) if invoice.pay_amount else None,
        qr_code_url=invoice.qr_code_url,
        payment_url=invoice.payment_url,
        status=invoice.status,
        provider_status=invoice.provider_status,
        tx_hash=invoice.tx_hash,
        expires_at=invoice.expires_at,
        paid_at=invoice.paid_at,
    )


def order_to_out(order: Order) -> OrderOut:
    invoice = order.active_invoice
    return OrderOut(
        id=order.id,
        order_code=order.order_code,
        customer_id=order.customer_id,
        customer_name=order.customer.display_name if order.customer else None,
        customer_username=order.customer.username if order.customer else None,
        customer_telegram_id=order.customer.telegram_id if order.customer else None,
        product_id=order.product_id,
        product_name=order.product_name,
        quantity=order.quantity,
        unit_price=float(order.unit_price),
        subtotal=float(order.subtotal),
        discount_amount=float(order.discount_amount),
        total_amount=float(order.total_amount),
        currency=order.currency,
        status=order.status,
        delivery_type=order.delivery_type,
        delivery_status=order.delivery_status,
        voucher_code=order.voucher_code,
        customer_note=order.customer_note,
        admin_note=order.admin_note,
        expires_at=order.expires_at,
        paid_at=order.paid_at,
        delivered_at=order.delivered_at,
        created_at=order.created_at,
        invoice=summarize_invoice(invoice) if invoice else None,
        delivery=DeliveryOut.model_validate(order.delivery) if order.delivery else None,
    )


async def create_order(
    session: AsyncSession,
    customer: Customer,
    product: Product,
    quantity: int,
    *,
    voucher_code: Optional[str] = None,
    note: Optional[str] = None,
    language: Optional[str] = None,
) -> Order:
    """Validate the cart, price it and request a gateway invoice."""
    if not product.is_active:
        raise ProductUnavailableError("Produk sedang tidak tersedia")
    quantity = max(1, int(quantity))
    if quantity < product.min_quantity:
        raise ValidationError(f"Minimal pembelian {product.min_quantity} item")
    if quantity > product.max_quantity:
        raise ValidationError(f"Maksimal pembelian {product.max_quantity} item")

    if product.delivery_type == DeliveryType.AUTO.value:
        available = await stock_service.count_available(session, product.id)
        if available < quantity:
            raise OutOfStock(
                f"Stok tidak cukup. Tersedia {available}, diminta {quantity}."
            )

    unit_price = float(product.price)
    subtotal = round(unit_price * quantity, 6)
    discount = 0.0
    voucher = None
    if voucher_code:
        try:
            voucher, discount = await voucher_service.validate_voucher(
                session, voucher_code, subtotal, customer.id
            )
        except voucher_service.VoucherError as exc:
            raise ValidationError(str(exc)) from exc

    total = round(subtotal - discount, 6)
    if total <= 0:
        raise ValidationError("Total pesanan harus lebih dari 0")

    order = Order(
        order_code=generate_order_code(),
        customer_id=customer.id,
        product_id=product.id,
        product_name=product.name_for(language or customer.language or "id"),
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal,
        discount_amount=discount,
        total_amount=total,
        currency=settings.payment_currency,
        status=OrderStatus.PENDING_PAYMENT.value,
        delivery_type=product.delivery_type,
        delivery_status=DeliveryStatus.PENDING.value,
        voucher_id=voucher.id if voucher else None,
        voucher_code=voucher.code if voucher else None,
        customer_note=note,
        language=language or customer.language or "id",
        expires_at=utcnow() + timedelta(minutes=settings.invoice_lifetime_minutes),
    )

    for _ in range(5):
        duplicate = await session.execute(
            select(Order.id).where(Order.order_code == order.order_code)
        )
        if duplicate.scalar_one_or_none() is None:
            break
        order.order_code = generate_order_code()

    session.add(order)
    await session.flush()

    if voucher is not None:
        await voucher_service.redeem_voucher(
            session, voucher, customer.id, order.id, discount
        )

    from app.services import payments

    await payments.create_invoice(session, order, customer)
    await session.flush()
    await session.refresh(order, attribute_names=["invoices"])
    return order


async def get_order(session: AsyncSession, order_id: int) -> Order:
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Pesanan tidak ditemukan")
    return order


async def get_by_code(session: AsyncSession, order_code: str) -> Optional[Order]:
    result = await session.execute(
        select(Order).where(Order.order_code == order_code.strip().upper())
    )
    return result.scalar_one_or_none()


async def list_orders(
    session: AsyncSession,
    *,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    product_id: Optional[int] = None,
    search: Optional[str] = None,
    paid_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[OrderOut], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    conditions = []
    if status:
        if "," in status:
            conditions.append(Order.status.in_([s.strip() for s in status.split(",") if s.strip()]))
        else:
            conditions.append(Order.status == status)
    if customer_id:
        conditions.append(Order.customer_id == customer_id)
    if product_id:
        conditions.append(Order.product_id == product_id)
    if paid_only:
        conditions.append(Order.status.in_(list(PAID_STATUSES)))
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Order.order_code.ilike(pattern),
                Order.product_name.ilike(pattern),
            )
        )

    count_query = select(func.count(Order.id))
    query = select(Order)
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.order_by(Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [order_to_out(order) for order in result.scalars().all()], total


async def customer_orders(
    session: AsyncSession, customer_id: int, limit: int = 10
) -> List[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_order_paid(
    session: AsyncSession, order: Order, paid_amount: Optional[float] = None
) -> bool:
    """Transition an order to PAID exactly once. Returns True on transition."""
    if order.status in PAID_STATUSES:
        return False

    now = utcnow()
    result = await session.execute(
        update(Order)
        .where(Order.id == order.id, Order.status.notin_(list(PAID_STATUSES)))
        .values(
            status=OrderStatus.PAID.value,
            paid_at=now,
            delivery_status=DeliveryStatus.PENDING.value,
            expires_at=None,
        )
    )
    if result.rowcount != 1:
        await session.refresh(order)
        return False

    await session.refresh(order)
    if order.customer is not None:
        await customer_service.register_sale(
            session, order.customer, float(order.total_amount)
        )

    await telegram_notify.send_message(
        order.customer.telegram_id if order.customer else 0,
        telegram_notify.order_paid_text(
            order.order_code,
            order.product_name,
            order.quantity,
            float(order.total_amount),
            order.currency,
            order.language,
        ),
    )
    await telegram_notify.notify_admins(
        telegram_notify.admin_new_order_text(
            order.order_code,
            order.product_name,
            order.quantity,
            float(order.total_amount),
            order.currency,
            order.delivery_type,
            order.customer.display_name if order.customer else "-",
        )
    )
    return True


async def mark_order_failed(
    session: AsyncSession, order: Order, reason: Optional[str] = None
) -> None:
    if order.status in PAID_STATUSES:
        return
    order.status = OrderStatus.FAILED.value
    order.admin_note = (f"Pembayaran gagal: {reason}" if reason else "Pembayaran gagal")[
        :500
    ]
    await voucher_service.release_redemption(session, order.id)
    await session.flush()


async def cancel_order(
    session: AsyncSession, order: Order, reason: Optional[str] = None
) -> Order:
    if order.status in PAID_STATUSES:
        raise ConflictError("Pesanan sudah dibayar dan tidak dapat dibatalkan")
    if order.status in FINAL_STATUSES:
        raise ConflictError("Pesanan sudah dalam status akhir")
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = utcnow()
    order.admin_note = (reason or "Dibatalkan oleh admin")[:500]
    invoices = await session.execute(
        select(PaymentInvoice).where(
            PaymentInvoice.order_id == order.id,
            PaymentInvoice.status.in_(
                [PaymentStatus.PENDING.value, PaymentStatus.CONFIRMING.value]
            ),
        )
    )
    for invoice in invoices.scalars().all():
        invoice.status = PaymentStatus.CANCELLED.value
    await voucher_service.release_redemption(session, order.id)
    await session.flush()
    return order


async def set_order_status(
    session: AsyncSession, order: Order, status: str, note: Optional[str] = None
) -> Order:
    try:
        target = OrderStatus(status)
    except ValueError as exc:
        raise ValidationError(f"Status pesanan tidak dikenal: {status}") from exc
    order.status = target.value
    if note:
        order.admin_note = note[:500]
    await session.flush()
    return order


async def cancel_expired_orders(session: AsyncSession) -> int:
    """Expire unpaid orders whose payment window elapsed."""
    now = utcnow()
    result = await session.execute(
        select(Order).where(
            Order.status == OrderStatus.PENDING_PAYMENT.value,
            Order.expires_at.is_not(None),
        )
    )
    expired = 0
    for order in result.scalars().all():
        deadline = as_aware(order.expires_at)
        if deadline is None or deadline > now:
            continue
        order.status = OrderStatus.EXPIRED.value
        order.cancelled_at = now
        await voucher_service.release_redemption(session, order.id)
        invoices = await session.execute(
            select(PaymentInvoice).where(
                PaymentInvoice.order_id == order.id,
                PaymentInvoice.status.in_(
                    [PaymentStatus.PENDING.value, PaymentStatus.CONFIRMING.value]
                ),
            )
        )
        for invoice in invoices.scalars().all():
            invoice.status = PaymentStatus.EXPIRED.value
        expired += 1
    if expired:
        await session.flush()
    return expired


async def list_transactions(
    session: AsyncSession,
    *,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[TransactionOut], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    conditions = []
    if status:
        conditions.append(Order.status == status)
    else:
        conditions.append(Order.status.in_(list(PAID_STATUSES) + [OrderStatus.REFUNDED.value]))
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Order.order_code.ilike(pattern),
                Order.product_name.ilike(pattern),
            )
        )

    count_query = select(func.count(Order.id))
    query = select(Order)
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.order_by(Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items: List[TransactionOut] = []
    for order in result.scalars().all():
        invoice = order.active_invoice
        items.append(
            TransactionOut(
                id=order.id,
                order_code=order.order_code,
                customer_name=order.customer.display_name if order.customer else None,
                product_name=order.product_name,
                amount=float(order.total_amount),
                currency=order.currency,
                status=order.status,
                delivery_status=order.delivery_status,
                provider=invoice.provider if invoice else None,
                tx_hash=invoice.tx_hash if invoice else None,
                network=invoice.network if invoice else None,
                created_at=order.created_at,
                paid_at=order.paid_at,
            )
        )
    return items, total


async def pending_manual_queue(
    session: AsyncSession, limit: int = 100
) -> List[Order]:
    result = await session.execute(
        select(Order)
        .where(
            Order.delivery_type == DeliveryType.MANUAL.value,
            Order.status.in_(
                [OrderStatus.PAID.value, OrderStatus.DELIVERED.value]
            ),
            Order.delivery_status.in_(
                [DeliveryStatus.PENDING.value, DeliveryStatus.PROCESSING.value,
                 DeliveryStatus.FAILED.value]
            ),
        )
        .order_by(Order.id.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
