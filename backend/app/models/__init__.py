"""Import every model so Base.metadata is complete before create_all()."""
from app.models.admin import Admin
from app.models.audit import AuditLog
from app.models.broadcast import Broadcast
from app.models.catalog import Category, Product
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.enums import (
    AdminRole,
    BroadcastAudience,
    BroadcastStatus,
    DeliveryMode,
    DeliveryStatus,
    DeliveryType,
    Language,
    OrderStatus,
    PaymentStatus,
    SenderType,
    TicketPriority,
    TicketStatus,
    VoucherType,
)
from app.models.order import Order
from app.models.payment import PaymentInvoice, WebhookEvent
from app.models.setting import NotificationTemplate, Setting
from app.models.stock import StockItem
from app.models.ticket import SupportTicket, TicketMessage
from app.models.voucher import Voucher, VoucherRedemption

__all__ = [
    "Admin",
    "AdminRole",
    "AuditLog",
    "Broadcast",
    "BroadcastAudience",
    "BroadcastStatus",
    "Category",
    "Customer",
    "Delivery",
    "DeliveryMode",
    "DeliveryStatus",
    "DeliveryType",
    "Language",
    "NotificationTemplate",
    "Order",
    "OrderStatus",
    "PaymentInvoice",
    "PaymentStatus",
    "Product",
    "SenderType",
    "Setting",
    "StockItem",
    "SupportTicket",
    "TicketMessage",
    "TicketPriority",
    "TicketStatus",
    "Voucher",
    "VoucherRedemption",
    "VoucherType",
    "WebhookEvent",
]