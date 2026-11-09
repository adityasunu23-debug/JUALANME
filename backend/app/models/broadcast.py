"""Bulk broadcast campaigns sent to customers."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import BroadcastAudience, BroadcastStatus


class Broadcast(Base, TimestampMixin):
    """A message blast queue item with delivery statistics."""

    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(
        String(16), default=BroadcastAudience.ALL.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default=BroadcastStatus.DRAFT.value, nullable=False, index=True
    )
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Broadcast {self.title} {self.status}>"