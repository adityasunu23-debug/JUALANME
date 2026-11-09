"""Manual delivery queue and delivery retries."""
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.deps import AuthContext, SessionDep, require_permission
from app.core.exceptions import NotFoundError
from app.models.delivery import Delivery
from app.models.enums import DeliveryStatus, DeliveryType
from app.models.order import Order
from app.schemas.common import Page
from app.schemas.order import DeliveryOut, ManualDeliveryRequest, OrderOut
from app.services import audit_service, delivery_service, order_service

router = APIRouter(tags=["deliveries"])

DeliveryCtx = Annotated[
    AuthContext, Depends(require_permission("delivery.manage"))
]


@router.get("/deliveries/queue", response_model=List[OrderOut])
async def manual_queue(ctx: DeliveryCtx, session: SessionDep) -> List[OrderOut]:
    orders = await order_service.pending_manual_queue(session)
    return [order_service.order_to_out(order) for order in orders]


@router.get("/deliveries", response_model=Page[DeliveryOut])
async def list_deliveries(
    ctx: DeliveryCtx,
    session: SessionDep,
    status: Optional[str] = None,
    mode: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[DeliveryOut]:
    conditions = []
    if status:
        conditions.append(Delivery.status == status)
    if mode:
        conditions.append(Delivery.mode == mode)

    count_query = select(func.count(Delivery.id))
    query = select(Delivery).order_by(Delivery.id.desc())
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    return Page[DeliveryOut].build(
        [DeliveryOut.model_validate(row) for row in result.scalars().all()],
        total,
        page,
        page_size,
    )


@router.get("/deliveries/failed", response_model=List[DeliveryOut])
async def failed_deliveries(
    ctx: DeliveryCtx, session: SessionDep
) -> List[DeliveryOut]:
    result = await session.execute(
        select(Delivery)
        .where(Delivery.status == DeliveryStatus.FAILED.value)
        .order_by(Delivery.id.desc())
        .limit(200)
    )
    return [DeliveryOut.model_validate(row) for row in result.scalars().all()]


@router.post("/deliveries/{delivery_id}/retry", response_model=DeliveryOut)
async def retry_delivery(
    delivery_id: int, ctx: DeliveryCtx, session: SessionDep
) -> DeliveryOut:
    delivery = await delivery_service.get_delivery(session, delivery_id)
    await delivery_service.retry_delivery(session, delivery)
    await audit_service.record(
        session, ctx.admin, "delivery.retry", "delivery", delivery.id,
        f"Percobaan ulang pengiriman #{delivery.id}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return DeliveryOut.model_validate(delivery)


@router.post("/orders/{order_id}/deliver", response_model=DeliveryOut)
async def deliver_manually(
    order_id: int,
    payload: ManualDeliveryRequest,
    ctx: DeliveryCtx,
    session: SessionDep,
) -> DeliveryOut:
    order = await order_service.get_order(session, order_id)
    delivery = await delivery_service.deliver_manual(
        session,
        order,
        ctx.admin,
        payload.content,
        note=payload.note,
        mark_completed=payload.mark_completed,
    )
    await audit_service.record(
        session, ctx.admin, "delivery.manual", "order", order.id,
        f"Pengiriman manual pesanan {order.order_code}", ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return DeliveryOut.model_validate(delivery)


@router.get("/deliveries/types", response_model=List[str])
async def delivery_types(ctx: DeliveryCtx) -> List[str]:
    return [item.value for item in DeliveryType]
