"""Customer lifecycle helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.customer import Customer
from app.models.enums import TicketStatus
from app.models.order import Order
from app.models.ticket import SupportTicket
from app.schemas.customer import CustomerDetail, CustomerOut, CustomerUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def to_out(customer: Customer) -> CustomerOut:
    return CustomerOut.model_validate(customer)


async def upsert_customer(
    session: AsyncSession,
    telegram_id: int,
    *,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language: Optional[str] = None,
) -> Customer:
    result = await session.execute(
        select(Customer).where(Customer.telegram_id == telegram_id)
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        customer = Customer(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language or "id",
            last_seen_at=_now(),
        )
        session.add(customer)
    else:
        if username is not None:
            customer.username = username
        if first_name is not None:
            customer.first_name = first_name
        if last_name is not None:
            customer.last_name = last_name
        if language:
            customer.language = language
        customer.last_seen_at = _now()
    await session.flush()
    return customer


async def get_customer(session: AsyncSession, customer_id: int) -> Customer:
    result = await session.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise NotFoundError("Pelanggan tidak ditemukan")
    return customer


async def get_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> Optional[Customer]:
    result = await session.execute(
        select(Customer).where(Customer.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def list_customers(
    session: AsyncSession,
    *,
    search: Optional[str] = None,
    blocked: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[CustomerOut], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    conditions = []
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Customer.username.ilike(pattern),
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
            )
        )
        if search.strip().lstrip("-").isdigit():
            conditions[-1] = or_(
                conditions[-1], Customer.telegram_id == int(search.strip())
            )
    if blocked is not None:
        conditions.append(Customer.is_blocked.is_(blocked))

    count_query = select(func.count(Customer.id))
    query = select(Customer)
    for condition in conditions:
        count_query = count_query.where(condition)
        query = query.where(condition)

    total = int((await session.execute(count_query)).scalar() or 0)
    result = await session.execute(
        query.order_by(Customer.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [to_out(c) for c in result.scalars().all()], total


async def update_customer(
    session: AsyncSession, customer_id: int, data: CustomerUpdate
) -> Customer:
    customer = await get_customer(session, customer_id)
    values = data.model_dump(exclude_unset=True)
    for key, value in values.items():
        if value is not None:
            setattr(customer, key, value)
    await session.flush()
    return customer


async def detail(session: AsyncSession, customer_id: int) -> CustomerDetail:
    customer = await get_customer(session, customer_id)
    orders = await session.execute(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.id.desc())
        .limit(10)
    )
    recent = [
        {
            "id": order.id,
            "order_code": order.order_code,
            "product_name": order.product_name,
            "quantity": order.quantity,
            "total_amount": float(order.total_amount),
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
        for order in orders.scalars().all()
    ]
    open_tickets = await session.execute(
        select(func.count(SupportTicket.id)).where(
            SupportTicket.customer_id == customer_id,
            SupportTicket.status.notin_(
                [TicketStatus.CLOSED.value, TicketStatus.ANSWERED.value]
            ),
        )
    )
    base = to_out(customer)
    return CustomerDetail(
        **base.model_dump(),
        recent_orders=recent,
        open_tickets=int(open_tickets.scalar() or 0),
    )


async def register_sale(
    session: AsyncSession, customer: Customer, amount: float
) -> None:
    customer.total_orders = int(customer.total_orders or 0) + 1
    customer.total_spent = float(customer.total_spent or 0) + float(amount)
    await session.flush()


async def new_customers_since(session: AsyncSession, since: datetime) -> int:
    result = await session.execute(
        select(func.count(Customer.id)).where(Customer.created_at >= since)
    )
    return int(result.scalar() or 0)


def start_of_day(moment: Optional[datetime] = None) -> datetime:
    value = moment or _now()
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def start_of_month(moment: Optional[datetime] = None) -> datetime:
    value = start_of_day(moment)
    return value.replace(day=1)


def last_days(days: int) -> datetime:
    return _now() - timedelta(days=days)
