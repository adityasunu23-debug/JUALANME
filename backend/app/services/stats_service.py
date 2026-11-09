"""Dashboard statistics, analytics and revenue reporting."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.catalog import Category, Product
from app.models.customer import Customer
from app.models.enums import OrderStatus, TicketStatus
from app.models.order import Order
from app.models.payment import PaymentInvoice
from app.models.stock import StockItem
from app.models.ticket import SupportTicket
from app.schemas.stats import (
    AnalyticsResponse,
    DashboardStats,
    NameValue,
    RevenueReport,
    TimeSeriesPoint,
)

PAID_STATUSES = (
    OrderStatus.PAID.value,
    OrderStatus.DELIVERED.value,
    OrderStatus.COMPLETED.value,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _day_start(moment: Optional[datetime] = None) -> datetime:
    value = moment or utcnow()
    return datetime.combine(value.date(), time.min, tzinfo=timezone.utc)


def _month_start(moment: Optional[datetime] = None) -> datetime:
    value = _day_start(moment)
    return value.replace(day=1)


def _date_str(value) -> str:
    return str(value)[:10]


async def _paid_revenue(session: AsyncSession, since: Optional[datetime] = None) -> float:
    query = select(func.coalesce(func.sum(Order.total_amount), 0)).where(
        Order.status.in_(list(PAID_STATUSES))
    )
    if since:
        query = query.where(Order.paid_at >= since)
    return float((await session.execute(query)).scalar() or 0)


async def _count(session: AsyncSession, query) -> int:
    return int((await session.execute(query)).scalar() or 0)


async def _series(
    session: AsyncSession,
    start: datetime,
    end: datetime,
    *,
    date_column,
    value_column,
    count_column,
    extra_condition=None,
) -> List[TimeSeriesPoint]:
    query = (
        select(
            func.date(date_column).label("day"),
            func.coalesce(func.sum(value_column), 0),
            func.count(count_column),
        )
        .where(date_column.is_not(None), date_column >= start, date_column <= end)
        .group_by(func.date(date_column))
        .order_by(func.date(date_column))
    )
    if extra_condition is not None:
        query = query.where(extra_condition)
    rows = (await session.execute(query)).all()
    data: Dict[str, TimeSeriesPoint] = {
        _date_str(row[0]): TimeSeriesPoint(
            date=_date_str(row[0]),
            revenue=float(row[1] or 0),
            orders=int(row[2] or 0),
        )
        for row in rows
    }
    points: List[TimeSeriesPoint] = []
    cursor = start.date()
    last = end.date()
    while cursor <= last:
        key = cursor.isoformat()
        points.append(
            data.get(key, TimeSeriesPoint(date=key, revenue=0, orders=0))
        )
        cursor += timedelta(days=1)
    return points


async def dashboard_stats(session: AsyncSession) -> DashboardStats:
    now = utcnow()
    today = _day_start(now)
    month = _month_start(now)

    revenue_total = await _paid_revenue(session)
    revenue_today = await _paid_revenue(session, today)
    revenue_month = await _paid_revenue(session, month)

    orders_total = await _count(session, select(func.count(Order.id)))
    orders_today = await _count(
        session, select(func.count(Order.id)).where(Order.created_at >= today)
    )
    orders_pending = await _count(
        session,
        select(func.count(Order.id)).where(
            Order.status == OrderStatus.PENDING_PAYMENT.value
        ),
    )
    orders_paid = await _count(
        session,
        select(func.count(Order.id)).where(Order.status.in_(list(PAID_STATUSES))),
    )
    customers_total = await _count(session, select(func.count(Customer.id)))
    customers_new_today = await _count(
        session, select(func.count(Customer.id)).where(Customer.created_at >= today)
    )
    products_total = await _count(session, select(func.count(Product.id)))
    stock_available = await _count(
        session,
        select(func.count(StockItem.id)).where(StockItem.is_used.is_(False)),
    )
    tickets_open = await _count(
        session,
        select(func.count(SupportTicket.id)).where(
            SupportTicket.status.notin_(
                [TicketStatus.CLOSED.value, TicketStatus.ANSWERED.value]
            )
        ),
    )

    status_rows = (
        await session.execute(
            select(Order.status, func.count(Order.id)).group_by(Order.status)
        )
    ).all()

    series = await _series(
        session,
        today - timedelta(days=13),
        now,
        date_column=Order.paid_at,
        value_column=Order.total_amount,
        count_column=Order.id,
        extra_condition=Order.status.in_(list(PAID_STATUSES)),
    )

    top_rows = (
        await session.execute(
            select(
                Order.product_name,
                func.sum(Order.quantity),
                func.sum(Order.total_amount),
            )
            .where(Order.status.in_(list(PAID_STATUSES)))
            .group_by(Order.product_name)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(5)
        )
    ).all()

    method_rows = (
        await session.execute(
            select(
                PaymentInvoice.provider,
                PaymentInvoice.network,
                func.count(PaymentInvoice.id),
            )
            .join(Order, Order.id == PaymentInvoice.order_id)
            .where(Order.status.in_(list(PAID_STATUSES)))
            .group_by(PaymentInvoice.provider, PaymentInvoice.network)
        )
    ).all()

    recent = (
        await session.execute(select(Order).order_by(Order.id.desc()).limit(8))
    ).scalars().all()

    return DashboardStats(
        revenue_total=revenue_total,
        revenue_today=revenue_today,
        revenue_month=revenue_month,
        orders_total=orders_total,
        orders_today=orders_today,
        orders_pending=orders_pending,
        orders_paid=orders_paid,
        customers_total=customers_total,
        customers_new_today=customers_new_today,
        products_total=products_total,
        stock_available=stock_available,
        tickets_open=tickets_open,
        conversion_rate=round((orders_paid / orders_total * 100), 2)
        if orders_total
        else 0,
        average_order_value=round(revenue_total / orders_paid, 2) if orders_paid else 0,
        revenue_series=series,
        orders_by_status=[
            NameValue(name=str(row[0]), value=float(row[1])) for row in status_rows
        ],
        top_products=[
            NameValue(name=str(row[0]), value=float(row[1] or 0), extra=float(row[2] or 0))
            for row in top_rows
        ],
        payment_methods=[
            NameValue(
                name=f"{row[0]} / {row[1]}".upper(), value=float(row[2] or 0)
            )
            for row in method_rows
        ],
        recent_orders=[
            {
                "id": order.id,
                "order_code": order.order_code,
                "customer": order.customer.display_name if order.customer else None,
                "product_name": order.product_name,
                "total_amount": float(order.total_amount),
                "status": order.status,
                "created_at": order.created_at.isoformat()
                if order.created_at
                else None,
            }
            for order in recent
        ],
    )


async def analytics(session: AsyncSession, days: int = 30) -> AnalyticsResponse:
    days = max(7, min(days, 365))
    now = utcnow()
    start = _day_start(now) - timedelta(days=days - 1)

    revenue_series = await _series(
        session,
        start,
        now,
        date_column=Order.paid_at,
        value_column=Order.total_amount,
        count_column=Order.id,
        extra_condition=Order.status.in_(list(PAID_STATUSES)),
    )
    growth_series = await _series(
        session,
        start,
        now,
        date_column=Customer.created_at,
        value_column=Customer.id,
        count_column=Customer.id,
    )
    for point in growth_series:
        point.revenue = 0

    status_rows = (
        await session.execute(
            select(Order.status, func.count(Order.id)).group_by(Order.status)
        )
    ).all()

    category_rows = (
        await session.execute(
            select(
                Category.name_id,
                func.coalesce(func.sum(Order.total_amount), 0),
                func.count(Order.id),
            )
            .join(Product, Product.id == Order.product_id)
            .join(Category, Category.id == Product.category_id)
            .where(Order.status.in_(list(PAID_STATUSES)))
            .group_by(Category.name_id)
            .order_by(func.sum(Order.total_amount).desc())
        )
    ).all()

    top_rows = (
        await session.execute(
            select(
                Order.product_name,
                func.sum(Order.quantity),
                func.sum(Order.total_amount),
            )
            .where(Order.status.in_(list(PAID_STATUSES)))
            .group_by(Order.product_name)
            .order_by(func.sum(Order.quantity).desc())
            .limit(10)
        )
    ).all()

    delivery_rows = (
        await session.execute(
            select(Order.delivery_type, func.count(Order.id)).group_by(
                Order.delivery_type
            )
        )
    ).all()

    return AnalyticsResponse(
        revenue_series=revenue_series,
        orders_by_status=[
            NameValue(name=str(row[0]), value=float(row[1])) for row in status_rows
        ],
        category_revenue=[
            NameValue(name=str(row[0]), value=float(row[1] or 0), extra=float(row[2] or 0))
            for row in category_rows
        ],
        top_products=[
            NameValue(name=str(row[0]), value=float(row[1] or 0), extra=float(row[2] or 0))
            for row in top_rows
        ],
        customer_growth=growth_series,
        delivery_breakdown=[
            NameValue(name=str(row[0]), value=float(row[1])) for row in delivery_rows
        ],
    )


PERIODS = {"today", "week", "month", "year", "all"}


async def revenue_report(
    session: AsyncSession,
    period: str = "month",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> RevenueReport:
    now = utcnow()
    if start_date or end_date:
        start = datetime.combine(
            start_date or date(now.year, 1, 1), time.min, tzinfo=timezone.utc
        )
        end = datetime.combine(
            end_date or now.date(), time.max, tzinfo=timezone.utc
        )
        period_label = f"{start.date()} - {end.date()}"
    elif period == "today":
        start, end = _day_start(now), now
        period_label = "today"
    elif period == "week":
        start, end = _day_start(now) - timedelta(days=6), now
        period_label = "week"
    elif period == "month":
        start, end = _month_start(now), now
        period_label = "month"
    elif period == "year":
        start, end = _day_start(now).replace(month=1, day=1), now
        period_label = "year"
    elif period == "all":
        start, end = datetime(2000, 1, 1, tzinfo=timezone.utc), now
        period_label = "all"
    else:
        raise ValidationError("Periode laporan tidak dikenal")

    paid_condition = Order.status.in_(list(PAID_STATUSES))
    range_condition = Order.paid_at.is_not(None), Order.paid_at >= start, Order.paid_at <= end

    totals = (
        await session.execute(
            select(
                func.coalesce(func.sum(Order.total_amount), 0),
                func.count(Order.id),
                func.coalesce(func.sum(Order.discount_amount), 0),
            ).where(paid_condition, *range_condition)
        )
    ).one()

    total_orders = await _count(
        session,
        select(func.count(Order.id)).where(
            Order.created_at >= start, Order.created_at <= end
        ),
    )
    refunded_row = await session.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.status == OrderStatus.REFUNDED.value,
            Order.created_at >= start,
            Order.created_at <= end,
        )
    )
    refunded = float(refunded_row.scalar() or 0)

    daily = await _series(
        session,
        start,
        end,
        date_column=Order.paid_at,
        value_column=Order.total_amount,
        count_column=Order.id,
        extra_condition=Order.status.in_(list(PAID_STATUSES)),
    )

    product_rows = (
        await session.execute(
            select(
                Order.product_name,
                func.sum(Order.total_amount),
                func.sum(Order.quantity),
            )
            .where(paid_condition, *range_condition)
            .group_by(Order.product_name)
            .order_by(func.sum(Order.total_amount).desc())
        )
    ).all()
    category_rows = (
        await session.execute(
            select(
                Category.name_id,
                func.sum(Order.total_amount),
                func.count(Order.id),
            )
            .join(Product, Product.id == Order.product_id)
            .join(Category, Category.id == Product.category_id)
            .where(paid_condition, *range_condition)
            .group_by(Category.name_id)
            .order_by(func.sum(Order.total_amount).desc())
        )
    ).all()

    gross = float(totals[0] or 0)
    paid_orders = int(totals[1] or 0)
    discount_total = float(totals[2] or 0)
    return RevenueReport(
        period=period_label,
        gross_revenue=gross,
        net_revenue=gross - float(refunded),
        total_orders=total_orders,
        paid_orders=paid_orders,
        refunded_amount=float(refunded),
        discount_total=discount_total,
        average_order_value=round(gross / paid_orders, 2) if paid_orders else 0,
        daily=daily,
        by_product=[
            NameValue(name=str(row[0]), value=float(row[1] or 0), extra=float(row[2] or 0))
            for row in product_rows
        ],
        by_category=[
            NameValue(name=str(row[0]), value=float(row[1] or 0), extra=float(row[2] or 0))
            for row in category_rows
        ],
    )
