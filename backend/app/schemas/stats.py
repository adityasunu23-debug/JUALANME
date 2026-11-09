"""Dashboard statistics and reporting schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class KpiCard(BaseModel):
    key: str
    label: str
    value: float = 0
    previous: float = 0
    change_percent: float = 0
    format: str = "number"


class TimeSeriesPoint(BaseModel):
    date: str
    revenue: float = 0
    orders: int = 0


class NameValue(BaseModel):
    name: str
    value: float = 0
    extra: Optional[float] = None


class DashboardStats(BaseModel):
    revenue_total: float = 0
    revenue_today: float = 0
    revenue_month: float = 0
    orders_total: int = 0
    orders_today: int = 0
    orders_pending: int = 0
    orders_paid: int = 0
    customers_total: int = 0
    customers_new_today: int = 0
    products_total: int = 0
    stock_available: int = 0
    tickets_open: int = 0
    conversion_rate: float = 0
    average_order_value: float = 0
    revenue_series: List[TimeSeriesPoint] = Field(default_factory=list)
    orders_by_status: List[NameValue] = Field(default_factory=list)
    top_products: List[NameValue] = Field(default_factory=list)
    payment_methods: List[NameValue] = Field(default_factory=list)
    recent_orders: List[dict] = Field(default_factory=list)


class AnalyticsResponse(BaseModel):
    revenue_series: List[TimeSeriesPoint] = Field(default_factory=list)
    orders_by_status: List[NameValue] = Field(default_factory=list)
    category_revenue: List[NameValue] = Field(default_factory=list)
    top_products: List[NameValue] = Field(default_factory=list)
    customer_growth: List[TimeSeriesPoint] = Field(default_factory=list)
    delivery_breakdown: List[NameValue] = Field(default_factory=list)


class RevenueReport(BaseModel):
    period: str
    gross_revenue: float = 0
    net_revenue: float = 0
    total_orders: int = 0
    paid_orders: int = 0
    refunded_amount: float = 0
    discount_total: float = 0
    average_order_value: float = 0
    daily: List[TimeSeriesPoint] = Field(default_factory=list)
    by_product: List[NameValue] = Field(default_factory=list)
    by_category: List[NameValue] = Field(default_factory=list)


class BackupResult(BaseModel):
    filename: str
    path: str
    size_bytes: int
    created_at: str
    tables: int = 0
    rows: int = 0


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    database: bool
    cache: str
    payment_provider: str
    bot_configured: bool