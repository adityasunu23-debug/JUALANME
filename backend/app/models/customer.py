"""Store customers (Telegram users)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    """A buyer identified by their Telegram account."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="id", nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[float] = mapped_column(
        Numeric(18, 6), default=0, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def display_name(self) -> str:
        full = " ".join(part for part in (self.first_name, self.last_name) if part)
        return full or (self.username or f"User {self.telegram_id}")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Customer id={self.id} tg={self.telegram_id}>"