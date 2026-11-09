"""Lightweight asyncio background jobs run inside the API process."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select

from app.core.config import settings
from app.db.session import session_scope
from app.models.enums import PaymentStatus
from app.models.payment import PaymentInvoice
from app.services import order_service, payments

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60
INVOICE_LOOKBACK_HOURS = 6

_tasks: List[asyncio.Task] = []
_stopping = asyncio.Event()


async def poll_pending_invoices() -> int:
    """Refresh invoices that are still awaiting funds."""
    updated = 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=INVOICE_LOOKBACK_HOURS)
    async with session_scope() as session:
        result = await session.execute(
            select(PaymentInvoice)
            .where(
                PaymentInvoice.status.in_(
                    [PaymentStatus.PENDING.value, PaymentStatus.CONFIRMING.value]
                ),
                PaymentInvoice.provider != "mock",
                PaymentInvoice.created_at >= cutoff,
            )
            .order_by(PaymentInvoice.id.asc())
            .limit(50)
        )
        invoices = list(result.scalars().all())
        for invoice in invoices:
            before = invoice.status
            await payments.refresh_invoice(session, invoice)
            if invoice.status != before:
                updated += 1
            await asyncio.sleep(0.1)
    return updated


async def expire_orders() -> int:
    async with session_scope() as session:
        return await order_service.cancel_expired_orders(session)


async def _poll_loop() -> None:
    while not _stopping.is_set():
        try:
            changed = await poll_pending_invoices()
            if changed:
                logger.info("Payment poller updated %s invoice(s)", changed)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - keep the loop alive
            logger.exception("Payment poller iteration failed")
        try:
            await asyncio.wait_for(_stopping.wait(), timeout=POLL_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


async def _expiry_loop() -> None:
    while not _stopping.is_set():
        try:
            expired = await expire_orders()
            if expired:
                logger.info("Expired %s unpaid order(s)", expired)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            logger.exception("Order expiry iteration failed")
        try:
            await asyncio.wait_for(_stopping.wait(), timeout=POLL_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


def start_workers() -> List[asyncio.Task]:
    """Start background jobs unless disabled through configuration."""
    if not settings.enable_workers:
        logger.info("Background workers disabled")
        return []
    _stopping.clear()
    _tasks.append(asyncio.create_task(_poll_loop(), name="invoice-poller"))
    _tasks.append(asyncio.create_task(_expiry_loop(), name="order-expiry"))
    logger.info("Background workers started: %s", [task.get_name() for task in _tasks])
    return list(_tasks)


async def stop_workers() -> None:
    _stopping.set()
    for task in list(_tasks):
        task.cancel()
    for task in list(_tasks):
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    _tasks.clear()
