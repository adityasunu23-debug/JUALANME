"""Customer orders."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import DeliveryStatus, DeliveryType, OrderStatus


class Order(Base, TimestampMixin):
    """A purchase made by a customer through the Telegram bot."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    discount_amount: Mapped[float] = mapped_column(
        Numeric(18, 6), default=0, nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USDT", nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=OrderStatus.PENDING_PAYMENT.value, nullable=False, index=True
    )
    delivery_type: Mapped[str] = mapped_column(
        String(16), default=DeliveryType.AUTO.value, nullable=False
    )
    delivery_status: Mapped[str] = mapped_column(
        String(24), default=DeliveryStatus.PENDING.value, nullable=False
    )
    voucher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vouchers.id", ondelete="SET NULL"), nullable=True
    )
    voucher_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    customer_note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="id", nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped["Customer"] = relationship(lazy="selectin")
    product: Mapped["Product"] = relationship(lazy="selectin")
    invoices: Mapped[list["PaymentInvoice"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )
    delivery: Mapped[Optional["Delivery"]] = relationship(
        back_populates="order", uselist=False, cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_paid(self) -> bool:
        return self.status in (
            OrderStatus.PAID.value,
            OrderStatus.DELIVERED.value,
            OrderStatus.COMPLETED.value,
        )

    @property
    def active_invoice(self) -> Optional["PaymentInvoice"]:
        for invoice in self.invoices:
            if invoice.status in ("PENDING", "CONFIRMING"):
                return invoice
        return self.invoices[-1] if self.invoices else None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.order_code} {self.status}>"