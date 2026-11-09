"""Customer and support ticket schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketPriority, TicketStatus


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: str = "id"
    is_blocked: bool = False
    total_orders: int = 0
    total_spent: float = 0
    notes: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class CustomerUpdate(BaseModel):
    is_blocked: Optional[bool] = None
    notes: Optional[str] = None
    language: Optional[str] = None


class CustomerDetail(CustomerOut):
    recent_orders: List[dict] = Field(default_factory=list)
    open_tickets: int = 0


class TicketMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_type: str
    sender_name: Optional[str] = None
    message: str
    is_read: bool = False
    created_at: Optional[datetime] = None


class TicketMessageCreate(BaseModel):
    message: str = Field(..., min_length=1)


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_code: str
    customer_id: int
    customer_name: Optional[str] = None
    customer_telegram_id: Optional[int] = None
    order_id: Optional[int] = None
    subject: str
    category: str
    status: str
    priority: str
    assigned_admin_id: Optional[int] = None
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    message_count: int = 0


class TicketDetail(TicketOut):
    messages: List[TicketMessageOut] = Field(default_factory=list)


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    priority: Optional[TicketPriority] = None
