"""Customer support tickets."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import TicketPriority, TicketStatus


class SupportTicket(Base, TimestampMixin):
    """A help request opened from the bot or the dashboard."""

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_code: Mapped[str] = mapped_column(
        String(24), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="general", nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=TicketStatus.OPEN.value, nullable=False, index=True
    )
    priority: Mapped[str] = mapped_column(
        String(16), default=TicketPriority.NORMAL.value, nullable=False
    )
    assigned_admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped["Customer"] = relationship(lazy="selectin")
    messages: Mapped[list["TicketMessage"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SupportTicket {self.ticket_code} {self.status}>"


class TicketMessage(Base, TimestampMixin):
    """A single message inside a ticket thread."""

    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False)
    sender_telegram_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TicketMessage ticket={self.ticket_id} {self.sender_type}>"