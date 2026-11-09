"""Customer directory endpoints."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.core.deps import AuthContext, SessionDep, require_permission
from app.schemas.common import Page
from app.schemas.customer import CustomerDetail, CustomerOut, CustomerUpdate
from app.services import audit_service, customer_service

router = APIRouter(prefix="/customers", tags=["customers"])

CustomerCtx = Annotated[
    AuthContext, Depends(require_permission("customers.manage"))
]


@router.get("", response_model=Page[CustomerOut])
async def list_customers(
    ctx: CustomerCtx,
    session: SessionDep,
    search: Optional[str] = None,
    blocked: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> Page[CustomerOut]:
    items, total = await customer_service.list_customers(
        session, search=search, blocked=blocked, page=page, page_size=page_size
    )
    return Page[CustomerOut].build(items, total, page, page_size)


@router.get("/{customer_id}", response_model=CustomerDetail)
async def get_customer(
    customer_id: int, ctx: CustomerCtx, session: SessionDep
) -> CustomerDetail:
    return await customer_service.detail(session, customer_id)


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: int, payload: CustomerUpdate, ctx: CustomerCtx, session: SessionDep
) -> CustomerOut:
    customer = await customer_service.update_customer(session, customer_id, payload)
    await audit_service.record(
        session, ctx.admin, "customer.update", "customer", customer.id,
        f"Memperbarui pelanggan {customer.display_name}",
        details=payload.model_dump(exclude_unset=True), ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
    await session.commit()
    return customer_service.to_out(customer)
