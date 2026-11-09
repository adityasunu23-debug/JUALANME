"""Domain enumerations shared by models, schemas and services.

Stored in the database as plain strings so the same schema runs on
PostgreSQL (production) and SQLite (local testing).
"""
from enum import Enum


class AdminRole(str, Enum):
    OWNER = "OWNER"
    SUPER_ADMIN = "SUPER_ADMIN"
    PRODUCT_ADMIN = "PRODUCT_ADMIN"
    ORDER_ADMIN = "ORDER_ADMIN"
    FINANCE_ADMIN = "FINANCE_ADMIN"
    SUPPORT_ADMIN = "SUPPORT_ADMIN"

    @property
    def label(self) -> str:
        return {
            AdminRole.OWNER: "Owner",
            AdminRole.SUPER_ADMIN: "Super Admin",
            AdminRole.PRODUCT_ADMIN: "Product Admin",
            AdminRole.ORDER_ADMIN: "Order Admin",
            AdminRole.FINANCE_ADMIN: "Finance Admin",
            AdminRole.SUPPORT_ADMIN: "Support Admin",
        }[self]


class DeliveryType(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class DeliveryMode(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    NOT_REQUIRED = "NOT_REQUIRED"


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMING = "CONFIRMING"
    PAID = "PAID"
    UNDERPAID = "UNDERPAID"
    OVERPAID = "OVERPAID"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class VoucherType(str, Enum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"
    CLOSED = "CLOSED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class SenderType(str, Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class BroadcastAudience(str, Enum):
    ALL = "ALL"
    BUYERS = "BUYERS"
    ACTIVE = "ACTIVE"


class BroadcastStatus(str, Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Language(str, Enum):
    ID = "id"
    EN = "en"
