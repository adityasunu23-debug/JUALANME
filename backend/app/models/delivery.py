"""Delivery records: automatic and manual fulfilment."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import DeliveryMode, DeliveryStatus


class Delivery(Base, TimestampMixin):
    """Fulfilment state of a paid order."""

    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(
        String(16), default=DeliveryMode.AUTO.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), default=DeliveryStatus.PENDING.value, nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    delivered_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stock_item_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivered_by_admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    order: Mapped["Order"] = relationship(back_populates="delivery")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Delivery order={self.order_id} {self.status}>"