"""Automatic and manual product delivery with retry support."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.admin import Admin
from app.models.catalog import Product
from app.models.delivery import Delivery
from app.models.enums import (
    DeliveryMode,
    DeliveryStatus,
    DeliveryType,
    OrderStatus,
)
from app.models.order import Order
from app.models.stock import StockItem
from app.services import settings_service, stock_service, telegram_notify

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def fulfill_order(session: AsyncSession, order: Order) -> Delivery:
    """Deliver a paid order according to the product delivery mode."""
    existing = await _existing_delivery(session, order.id)
    if existing is not None:
        if existing.status == DeliveryStatus.DELIVERED.value:
            return existing
        if existing.mode == DeliveryMode.MANUAL.value:
            return existing
        if existing.attempts >= MAX_ATTEMPTS:
            return existing
        await _attempt_auto(session, order, existing)
        return existing

    auto_enabled = await settings_service.get_bool(
        session, "delivery.auto_enabled", default=True
    )
    is_auto = (
        order.delivery_type == DeliveryType.AUTO.value
        and auto_enabled
        and not (order.product and not order.product.is_active)
    )
    delivery = Delivery(
        order_id=order.id,
        product_id=order.product_id,
        mode=DeliveryMode.AUTO.value if is_auto else DeliveryMode.MANUAL.value,
        status=DeliveryStatus.PENDING.value,
        quantity=order.quantity,
        attempts=0,
    )
    session.add(delivery)
    await session.flush()
    order.delivery_status = DeliveryStatus.PENDING.value

    if is_auto:
        await _attempt_auto(session, order, delivery)
    else:
        if order.delivery_type == DeliveryType.AUTO.value and not auto_enabled:
            order.admin_note = "Pengiriman otomatis nonaktif; diproses manual."
        await telegram_notify.notify_admins(
            telegram_notify.manual_delivery_needed_text(
                order.order_code,
                order.product_name,
                order.quantity,
                order.customer.display_name if order.customer else "-",
            )
        )
    await session.flush()
    return delivery


async def _existing_delivery(
    session: AsyncSession, order_id: int
) -> Optional[Delivery]:
    result = await session.execute(
        select(Delivery).where(Delivery.order_id == order_id)
    )
    return result.scalar_one_or_none()


async def _attempt_auto(
    session: AsyncSession, order: Order, delivery: Delivery
) -> None:
    """Claim stock and mark the order completed. Safe to call repeatedly."""
    delivery.attempts = int(delivery.attempts or 0) + 1
    delivery.status = DeliveryStatus.PROCESSING.value
    order.delivery_status = DeliveryStatus.PROCESSING.value
    await session.flush()

    try:
        items = await stock_service.reserve_stock(
            session, order.product_id, order.quantity, order.id
        )
    except stock_service.OutOfStockError as exc:
        delivery.status = DeliveryStatus.FAILED.value
        delivery.last_error = str(exc)[:500]
        order.delivery_status = DeliveryStatus.FAILED.value
        order.admin_note = f"Pengiriman otomatis gagal: stok tidak cukup"[:500]
        await telegram_notify.notify_admins(
            "<b>Pengiriman otomatis gagal</b>\n"
            f"Pesanan <code>{order.order_code}</code> ({order.product_name} x{order.quantity})\n"
            f"Alasan: {telegram_notify.escape(str(exc))}\n"
            "Silakan proses manual dari dashboard."
        )
        await session.flush()
        return
    except Exception as exc:  # unexpected stock/database failure
        delivery.status = DeliveryStatus.FAILED.value
        delivery.last_error = str(exc)[:500]
        order.delivery_status = DeliveryStatus.FAILED.value
        logger.exception("Unexpected delivery error for %s", order.order_code)
        await session.flush()
        return

    content = "\n".join(_format_item(item) for item in items)
    delivery.delivered_content = content
    delivery.stock_item_ids = [item.id for item in items]
    delivery.status = DeliveryStatus.DELIVERED.value
    delivery.last_error = None
    delivery.delivered_at = utcnow()
    delivery.notified_at = utcnow()

    order.delivery_status = DeliveryStatus.DELIVERED.value
    order.status = OrderStatus.COMPLETED.value
    order.delivered_at = utcnow()
    order.completed_at = utcnow()
    order.admin_note = None

    product = await session.get(Product, order.product_id)
    if product is not None:
        product.sold_count = int(product.sold_count or 0) + order.quantity

    await session.flush()
    await telegram_notify.send_message(
        order.customer.telegram_id if order.customer else 0,
        telegram_notify.order_delivered_text(
            order.order_code, order.product_name, content, order.language
        ),
    )


def _format_item(item: StockItem) -> str:
    if item.label:
        return f"{item.label}: {item.content}"
    return item.content


async def deliver_manual(
    session: AsyncSession,
    order: Order,
    admin: Optional[Admin],
    content: str,
    *,
    note: Optional[str] = None,
    mark_completed: bool = True,
) -> Delivery:
    if not content or not content.strip():
        raise ConflictError("Konten pengiriman tidak boleh kosong")
    delivery = await _existing_delivery(session, order.id)
    if delivery is None:
        delivery = Delivery(
            order_id=order.id,
            product_id=order.product_id,
            mode=DeliveryMode.MANUAL.value,
            quantity=order.quantity,
        )
        session.add(delivery)
        await session.flush()

    delivery.mode = DeliveryMode.MANUAL.value
    delivery.status = DeliveryStatus.DELIVERED.value
    delivery.delivered_content = content.strip()
    delivery.attempts = int(delivery.attempts or 0) + 1
    delivery.last_error = None
    delivery.delivered_by_admin_id = admin.id if admin else None
    delivery.delivered_at = utcnow()
    delivery.notified_at = utcnow()

    order.delivery_status = DeliveryStatus.DELIVERED.value
    order.delivered_at = utcnow()
    if mark_completed:
        order.status = OrderStatus.COMPLETED.value
        order.completed_at = utcnow()
    if note:
        order.admin_note = note[:500]

    product = await session.get(Product, order.product_id)
    if product is not None:
        product.sold_count = int(product.sold_count or 0) + order.quantity

    await session.flush()
    await telegram_notify.send_message(
        order.customer.telegram_id if order.customer else 0,
        telegram_notify.order_delivered_text(
            order.order_code, order.product_name, delivery.delivered_content,
            order.language,
        ),
    )
    return delivery


async def get_delivery(session: AsyncSession, delivery_id: int) -> Delivery:
    delivery = await session.get(Delivery, delivery_id)
    if delivery is None:
        raise NotFoundError("Data pengiriman tidak ditemukan")
    return delivery


async def retry_delivery(session: AsyncSession, delivery: Delivery) -> Delivery:
    if delivery.status == DeliveryStatus.DELIVERED.value:
        raise ConflictError("Pesanan sudah terkirim")
    if int(delivery.attempts or 0) >= MAX_ATTEMPTS:
        raise ConflictError(
            f"Batas percobaan ({MAX_ATTEMPTS}x) tercapai. Gunakan pengiriman manual."
        )
    order = await session.get(Order, delivery.order_id)
    if order is None:
        raise NotFoundError("Pesanan tidak ditemukan")

    if delivery.mode == DeliveryMode.AUTO.value:
        await _attempt_auto(session, order, delivery)
    else:
        delivery.status = DeliveryStatus.PROCESSING.value
        order.delivery_status = DeliveryStatus.PROCESSING.value
    await session.flush()
    return delivery
