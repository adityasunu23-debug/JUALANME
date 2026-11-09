"""Product catalogue: categories and products."""
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import DeliveryType


class Category(Base, TimestampMixin):
    """A catalogue group shown as a button in the bot."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    description_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(16), default="*", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    def name_for(self, language: str) -> str:
        return self.name_en if language == "en" else self.name_id

    def description_for(self, language: str) -> str:
        value = self.description_en if language == "en" else self.description_id
        return value or ""

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category {self.slug}>"


class Product(Base, TimestampMixin):
    """A digital product sold through the bot."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sku: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    name_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    description_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    compare_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USDT", nullable=False)
    delivery_type: Mapped[str] = mapped_column(
        String(16), default=DeliveryType.AUTO.value, nullable=False
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    min_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category: Mapped[Optional[Category]] = relationship(back_populates="products")
    stock_items: Mapped[list["StockItem"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def name_for(self, language: str) -> str:
        return self.name_en if language == "en" else self.name_id

    def description_for(self, language: str) -> str:
        value = self.description_en if language == "en" else self.description_id
        return value or ""

    @property
    def is_auto(self) -> bool:
        return self.delivery_type == DeliveryType.AUTO.value

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product id={self.id} {self.name_id}>"