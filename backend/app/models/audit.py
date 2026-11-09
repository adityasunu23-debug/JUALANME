"""Audit trail of every privileged dashboard action."""
from typing import Optional

from sqlalchemy import BigInteger, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Immutable record of an admin action."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_resource", "resource", "resource_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    admin_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    admin_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="SUCCESS", nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action} {self.resource}:{self.resource_id}>"