"""Administrator accounts used for dashboard access and RBAC."""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import AdminRole


class Admin(Base, TimestampMixin):
    """A dashboard operator authenticated through the Telegram Login Widget."""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    role: Mapped[str] = mapped_column(
        String(32), default=AdminRole.SUPPORT_ADMIN.value, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    @property
    def role_enum(self) -> AdminRole:
        try:
            return AdminRole(self.role)
        except ValueError:
            return AdminRole.SUPPORT_ADMIN

    @property
    def display_name(self) -> str:
        full = " ".join(part for part in (self.first_name, self.last_name) if part)
        return full or (self.username or f"Admin #{self.id}")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Admin id={self.id} tg={self.telegram_id} role={self.role}>"
