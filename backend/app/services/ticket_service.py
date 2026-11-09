"""Customer support tickets."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.customer import Customer
from app.models.enums import SenderType, TicketPriority, TicketStatus
from app.models.order import Order
from app.models.ticket import SupportTicket, TicketMessage
from app.schemas.customer import (
    TicketDetail,
    TicketMessageOut,
    TicketOut,
    TicketStatusUpdate,
)
from app.services import telegram_notify


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_ticket_code() -> str:
    return "TKT-" + utcnow().strftime("%y%m%d") + "-" + secrets.token_hex(2).upper()


def ticket_out(ticket: SupportTicket) -> TicketOut:
    customer = ticket.customer
    return TicketOut(
        id=ticket.id,
        ticket_code=ticket.ticket_code,
        customer_id=ticket.customer_id,
        customer_name=customer.display_name if customer else None,
        customer_telegram_id=customer.telegram_id if customer else None,
        order_id=ticket.order_id,
        subject=ticket.subject,
        category=ticket.category,
        status=ticket.status,
        priority=ticket.priority,
        assigned_admin_id=ticket.assigned_admin_id,
        last_message_at=ticket.last_message_at,
        created_at=ticket.created_at,
        message_count=len(ticket.messages or []),
    )


def ticket_detail(ticket: SupportTicket) -> TicketDetail:
    base = ticket_out(ticket)
    return TicketDetail(
        **base.model_dump(),
        messages=[
            TicketMessageOut.model_validate(message) for message in ticket.messages
        ],
    )


async def get_ticket(session: AsyncSession, ticket_id: int) -> SupportTicket:
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise NotFoundError("Tiket tidak ditemukan")
    return ticket


async def create_ticket(
    session: AsyncSession,
    customer: Customer,
    subject: str,
    message: str,
    *,
    category: str = "general",
    order_id: Optional[int] = None,
    priority: str = TicketPriority.NORMAL.value,
) -> SupportTicket:
    subject = (subject or "").strip()[:200]
    body = (message or "").strip()
    if not subject or not body:
        raise ConflictError("Subjek dan pesan tiket wajib diisi")
    if order_id:
        owner_check = await session.execute(
            select(Order.id).where(
                Order.id == order_id, Order.customer_id == customer.id
            )
        )
        if owner_check.scalar_one_or_none() is None:
            order_id = None

    ticket = SupportTicket(
        ticket_code=generate_ticket_code(),
        customer_id=customer.id,
        order_id=order_id,
        subject=subject,
        category=category or "general",
        status=TicketStatus.OPEN.value,
        priority=priority or TicketPriority.NORMAL.value,
        last_message_at=utcnow(),
    )
    session.add(ticket)
    await session.flush()
    session.add(
        TicketMessage(
            ticket_id=ticket.id,
            sender_type=SenderType.CUSTOMER.value,
            sender_telegram_id=customer.telegram_id,
            sender_name=customer.display_name,
            message=body,
        )
    )
    await session.flush()
    await session.refresh(ticket)
    return ticket


async def add_message(
    session: AsyncSession,
    ticket: SupportTicket,
    message: str,
    *,
    sender_type: str,
    sender_name: Optional[str] = None,
    sender_telegram_id: Optional[int] = None,
    notify_customer: bool = False,
) -> TicketMessage:
    body = (message or "").strip()
    if not body:
        raise ConflictError("Pesan tidak boleh kosong")
    if ticket.status == TicketStatus.CLOSED.value:
        raise ConflictError("Tiket sudah ditutup")

    entry = TicketMessage(
        ticket_id=ticket.id,
        sender_type=sender_type,
        sender_telegram_id=sender_telegram_id,
        sender_name=sender_name,
        message=body,
        is_read=sender_type == SenderType.ADMIN.value,
    )
    session.add(entry)
    ticket.last_message_at = utcnow()
    if sender_type == SenderType.ADMIN.value:
        ticket.status = TicketStatus.ANSWERED.value
    elif sender_type == SenderType.CUSTOMER.value:
        ticket.status = TicketStatus.OPEN.value
    await session.flush()

    if notify_customer and ticket.customer is not None:
        await telegram_notify.send_message(
            ticket.customer.telegram_id,
            (
                "<b>Balasan dari support</b>\n"
                f"Tiket <code>{telegram_notify.escape(ticket.ticket_code)}</code>\n\n"
                f"{telegram_notify.escape(body)}"
            ),
        )
    return entry


async def list_tickets(
    session: AsyncSession,
    *,
    status: Optional[str] = None,
    search: Optional[str] = None,
    customer_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[TicketOut], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    conditions = []
    if status:
        conditions.append(SupportTicket.status == status)
    if customer_id:
        conditions.append(SupportTicket.customer_id == customer_id)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                SupportTicket.subject.ilike(pattern),
                SupportTicket.ticket_code.ilike(pattern),
            )
        )

    count_query = select(func.count(SupportTicket.id))
    query = select(SupportTicket)
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.order_by(SupportTicket.last_message_at.desc().nullslast(),
                       SupportTicket.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [ticket_out(ticket) for ticket in result.scalars().all()], total


async def update_status(
    session: AsyncSession, ticket: SupportTicket, data: TicketStatusUpdate
) -> SupportTicket:
    ticket.status = data.status.value
    if data.priority:
        ticket.priority = data.priority.value
    if data.status == TicketStatus.CLOSED:
        ticket.closed_at = utcnow()
    await session.flush()
    return ticket
