"""Key/value store for runtime configuration (API keys, notifications, toggles)."""
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    """A single configurable value managed from the admin dashboard."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(96), unique=True, nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    group: Mapped[str] = mapped_column(String(48), default="general", nullable=False, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    value_type: Mapped[str] = mapped_column(String(16), default="string", nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_editable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Setting {self.key}>"


class NotificationTemplate(Base, TimestampMixin):
    """Localised message template overridable from the dashboard."""

    __tablename__ = "notification_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(8), default="id", nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<NotificationTemplate {self.code}:{self.language}>"