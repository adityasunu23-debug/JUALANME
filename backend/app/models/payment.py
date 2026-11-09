"""Crypto payment invoices and raw gateway webhook events."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import PaymentStatus


class PaymentInvoice(Base, TimestampMixin):
    """An invoice created at the payment gateway for a single order."""

    __tablename__ = "payment_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(24), default="cryptomus", nullable=False)
    provider_invoice_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    provider_order_ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    paid_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USDT", nullable=False)
    network: Mapped[str] = mapped_column(String(16), default="bep20", nullable=False)
    pay_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    pay_amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    payer_currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    qr_code_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    payment_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), default=PaymentStatus.PENDING.value, nullable=False, index=True
    )
    provider_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    confirmations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="invoices")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaymentInvoice {self.provider_invoice_id} {self.status}>"


class WebhookEvent(Base, TimestampMixin):
    """Raw webhook payload, kept for replay, auditing and duplicate protection."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    payload_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    provider_invoice_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WebhookEvent {self.provider} {self.event_type} processed={self.processed}>"