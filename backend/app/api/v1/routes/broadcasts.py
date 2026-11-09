"""Marketing broadcast endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import AuthContext, SessionDep, require_permission
from app.schemas.common import MessageResponse, Page
from app.schemas.marketing import BroadcastCreate, BroadcastOut
from app.services import audit_service, broadcast_service

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])

BroadcastCtx = Annotated[
    AuthContext, Depends(require_permission("broadcast.manage"))
]


@router.get("", response_model=Page[BroadcastOut])
async def list_broadcasts(
    ctx: BroadcastCtx,
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[BroadcastOut]:
    items, total = await broadcast_service.list_broadcasts(session, page, page_size)
    return Page[BroadcastOut].build(items, total, page, page_size)


@router.post("", response_model=BroadcastOut, status_code=201)
async def create_broadcast(
    payload: BroadcastCreate, ctx: BroadcastCtx, session: SessionDep
) -> BroadcastOut:
    broadcast = await broadcast_service.create_broadcast(
        session, payload, admin_id=ctx.admin.id
    )
    if payload.send_now:
        await broadcast_service.run_broadcast(session, broadcast.id)
    await audit_service.record(
        session, ctx.admin, "broadcast.create", "broadcast", broadcast.id,
        f"Membuat broadcast {broadcast.title}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    await session.refresh(broadcast)
    return BroadcastOut.model_validate(broadcast)


@router.post("/{broadcast_id}/run", response_model=BroadcastOut)
async def run_broadcast(
    broadcast_id: int, ctx: BroadcastCtx, session: SessionDep
) -> BroadcastOut:
    broadcast = await broadcast_service.run_broadcast(session, broadcast_id)
    await audit_service.record(
        session, ctx.admin, "broadcast.run", "broadcast", broadcast.id,
        f"Mengirim broadcast {broadcast.title}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return BroadcastOut.model_validate(broadcast)


@router.delete("/{broadcast_id}", response_model=MessageResponse)
async def delete_broadcast(
    broadcast_id: int, ctx: BroadcastCtx, session: SessionDep
) -> MessageResponse:
    await broadcast_service.delete_broadcast(session, broadcast_id)
    await audit_service.record(
        session, ctx.admin, "broadcast.delete", "broadcast", broadcast_id,
        "Menghapus broadcast", ip_address=ctx.ip, user_agent=ctx.user_agent,
    )
    await session.commit()
    return MessageResponse(message="Broadcast dihapus")
