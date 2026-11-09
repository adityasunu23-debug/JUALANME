"""Discount vouchers and their redemptions."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import VoucherType


class Voucher(Base, TimestampMixin):
    """A promotional code applied to an order."""

    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    type: Mapped[str] = mapped_column(
        String(16), default=VoucherType.PERCENT.value, nullable=False
    )
    value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    min_purchase: Mapped[float] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    max_discount: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    usage_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    per_customer_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Voucher {self.code}>"


class VoucherRedemption(Base, TimestampMixin):
    """Tracks per-customer voucher usage."""

    __tablename__ = "voucher_redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        ForeignKey("vouchers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    discount_amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VoucherRedemption voucher={self.voucher_id} customer={self.customer_id}>"