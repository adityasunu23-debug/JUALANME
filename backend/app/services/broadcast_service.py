"""Broadcast campaigns sent to customer segments."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.broadcast import Broadcast
from app.models.customer import Customer
from app.models.enums import BroadcastAudience, BroadcastStatus
from app.schemas.marketing import BroadcastCreate, BroadcastOut
from app.services import telegram_notify


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def list_broadcasts(
    session: AsyncSession, page: int = 1, page_size: int = 20
) -> Tuple[List[BroadcastOut], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    total = int(
        (await session.execute(select(func.count(Broadcast.id)))).scalar() or 0
    )
    result = await session.execute(
        select(Broadcast)
        .order_by(Broadcast.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [BroadcastOut.model_validate(row) for row in result.scalars().all()], total


async def get_broadcast(session: AsyncSession, broadcast_id: int) -> Broadcast:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        raise NotFoundError("Broadcast tidak ditemukan")
    return broadcast


async def create_broadcast(
    session: AsyncSession, data: BroadcastCreate, admin_id: Optional[int] = None
) -> Broadcast:
    broadcast = Broadcast(
        title=data.title,
        message=data.message,
        audience=data.audience.value,
        status=BroadcastStatus.DRAFT.value,
        created_by_admin_id=admin_id,
    )
    session.add(broadcast)
    await session.flush()
    return broadcast


async def delete_broadcast(session: AsyncSession, broadcast_id: int) -> None:
    broadcast = await get_broadcast(session, broadcast_id)
    if broadcast.status == BroadcastStatus.SENDING.value:
        raise ConflictError("Broadcast sedang dikirim")
    await session.delete(broadcast)
    await session.flush()


async def _recipients(session: AsyncSession, audience: str) -> List[Customer]:
    query = select(Customer).where(Customer.is_blocked.is_(False))
    if audience == BroadcastAudience.BUYERS.value:
        query = query.where(Customer.total_orders > 0)
    elif audience == BroadcastAudience.ACTIVE.value:
        query = query.where(
            Customer.last_seen_at.is_not(None),
            Customer.last_seen_at >= utcnow() - timedelta(days=30),
        )
    result = await session.execute(query)
    return list(result.scalars().all())


async def run_broadcast(
    session: AsyncSession, broadcast_id: int
) -> Broadcast:
    """Send a campaign to every recipient. Errors are counted, never raised."""
    broadcast = await get_broadcast(session, broadcast_id)
    if broadcast.status == BroadcastStatus.SENDING.value:
        raise ConflictError("Broadcast sedang dikirim")
    if broadcast.status == BroadcastStatus.SENT.value:
        raise ConflictError("Broadcast sudah terkirim")

    recipients = await _recipients(session, broadcast.audience)
    broadcast.status = BroadcastStatus.SENDING.value
    broadcast.total_recipients = len(recipients)
    broadcast.sent_count = 0
    broadcast.failed_count = 0
    broadcast.started_at = utcnow()
    await session.flush()

    for customer in recipients:
        ok = await telegram_notify.send_message(customer.telegram_id, broadcast.message)
        if ok:
            broadcast.sent_count = int(broadcast.sent_count or 0) + 1
        else:
            broadcast.failed_count = int(broadcast.failed_count or 0) + 1
        await asyncio.sleep(0.05)

    broadcast.status = (
        BroadcastStatus.SENT.value
        if broadcast.failed_count == 0
        else BroadcastStatus.FAILED.value
    )
    broadcast.finished_at = utcnow()
    await session.flush()
    return broadcast
