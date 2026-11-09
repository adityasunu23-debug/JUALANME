"""Inventory items delivered to customers."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class StockItem(Base, TimestampMixin):
    """One deliverable unit (account, key, code). Locked atomically on delivery."""

    __tablename__ = "stock_items"
    __table_args__ = (
        Index("ix_stock_items_product_used", "product_id", "is_used"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    is_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reserved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String(24), default="manual", nullable=False)
    batch_id: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="stock_items")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StockItem id={self.id} product={self.product_id} used={self.is_used}>"