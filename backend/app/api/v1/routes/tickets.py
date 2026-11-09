"""Support ticket inbox."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import AuthContext, SessionDep, require_permission
from app.models.enums import SenderType
from app.schemas.common import Page
from app.schemas.customer import (
    TicketDetail,
    TicketMessageCreate,
    TicketOut,
    TicketStatusUpdate,
)
from app.services import audit_service, ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])

TicketCtx = Annotated[AuthContext, Depends(require_permission("tickets.manage"))]


@router.get("", response_model=Page[TicketOut])
async def list_tickets(
    ctx: TicketCtx,
    session: SessionDep,
    status: Optional[str] = None,
    search: Optional[str] = None,
    customer_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[TicketOut]:
    items, total = await ticket_service.list_tickets(
        session,
        status=status,
        search=search,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )
    return Page[TicketOut].build(items, total, page, page_size)


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(
    ticket_id: int, ctx: TicketCtx, session: SessionDep
) -> TicketDetail:
    ticket = await ticket_service.get_ticket(session, ticket_id)
    return ticket_service.ticket_detail(ticket)


@router.post("/{ticket_id}/reply", response_model=TicketDetail)
async def reply_ticket(
    ticket_id: int,
    payload: TicketMessageCreate,
    ctx: TicketCtx,
    session: SessionDep,
) -> TicketDetail:
    ticket = await ticket_service.get_ticket(session, ticket_id)
    await ticket_service.add_message(
        session,
        ticket,
        payload.message,
        sender_type=SenderType.ADMIN.value,
        sender_name=ctx.admin.display_name,
        sender_telegram_id=ctx.admin.telegram_id,
        notify_customer=True,
    )
    ticket.assigned_admin_id = ctx.admin.id
    await session.flush()
    await audit_service.record(
        session, ctx.admin, "ticket.reply", "ticket", ticket.id,
        f"Balasan tiket {ticket.ticket_code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    await session.refresh(ticket)
    return ticket_service.ticket_detail(ticket)


@router.patch("/{ticket_id}/status", response_model=TicketDetail)
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    ctx: TicketCtx,
    session: SessionDep,
) -> TicketDetail:
    ticket = await ticket_service.get_ticket(session, ticket_id)
    await ticket_service.update_status(session, ticket, payload)
    await audit_service.record(
        session, ctx.admin, "ticket.status", "ticket", ticket.id,
        f"Status tiket {ticket.ticket_code} -> {ticket.status}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    await session.refresh(ticket)
    return ticket_service.ticket_detail(ticket)
