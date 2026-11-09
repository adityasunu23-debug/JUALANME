"""Order and delivery schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderItemSummary(BaseModel):
    product_id: int
    name: str
    quantity: int
    unit_price: float


class InvoiceSummary(BaseModel):
    id: int
    provider: str
    provider_invoice_id: Optional[str] = None
    amount: float
    paid_amount: Optional[float] = None
    currency: str
    network: str
    pay_address: Optional[str] = None
    pay_amount: Optional[float] = None
    qr_code_url: Optional[str] = None
    payment_url: Optional[str] = None
    status: str
    provider_status: Optional[str] = None
    tx_hash: Optional[str] = None
    expires_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int
    mode: str
    status: str
    quantity: int
    delivered_content: Optional[str] = None
    attempts: int = 0
    last_error: Optional[str] = None
    delivered_by_admin_id: Optional[int] = None
    delivered_at: Optional[datetime] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_code: str
    customer_id: int
    customer_name: Optional[str] = None
    customer_username: Optional[str] = None
    customer_telegram_id: Optional[int] = None
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float
    discount_amount: float
    total_amount: float
    currency: str
    status: str
    delivery_type: str
    delivery_status: str
    voucher_code: Optional[str] = None
    customer_note: Optional[str] = None
    admin_note: Optional[str] = None
    expires_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    invoice: Optional[InvoiceSummary] = None
    delivery: Optional[DeliveryOut] = None


class OrderNoteUpdate(BaseModel):
    admin_note: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class ManualDeliveryRequest(BaseModel):
    content: str = Field(..., description="Deliverable text shown to the customer")
    note: Optional[str] = None
    mark_completed: bool = True


class TransactionOut(BaseModel):
    id: int
    order_code: str
    customer_name: Optional[str] = None
    product_name: str
    amount: float
    currency: str
    status: str
    delivery_status: str
    provider: Optional[str] = None
    tx_hash: Optional[str] = None
    network: Optional[str] = None
    created_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class TransactionListResponse(BaseModel):
    items: List[TransactionOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
