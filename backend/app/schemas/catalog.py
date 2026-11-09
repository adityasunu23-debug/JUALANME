"""Catalogue schemas: categories and products."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeliveryType


class CategoryBase(BaseModel):
    slug: str = Field(..., max_length=64)
    name_id: str = Field(..., max_length=128)
    name_en: str = Field(..., max_length=128)
    description_id: Optional[str] = None
    description_en: Optional[str] = None
    icon: str = "*"
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    slug: Optional[str] = None
    name_id: Optional[str] = None
    name_en: Optional[str] = None
    description_id: Optional[str] = None
    description_en: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryOut(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_count: int = 0
    created_at: Optional[datetime] = None


class ProductBase(BaseModel):
    category_id: Optional[int] = None
    sku: Optional[str] = None
    name_id: str = Field(..., max_length=160)
    name_en: str = Field(..., max_length=160)
    description_id: Optional[str] = None
    description_en: Optional[str] = None
    price: float = Field(..., ge=0)
    compare_price: Optional[float] = None
    currency: str = "USDT"
    delivery_type: DeliveryType = DeliveryType.AUTO
    image_url: Optional[str] = None
    min_quantity: int = Field(1, ge=1)
    max_quantity: int = Field(100, ge=1)
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0
    delivery_instructions: Optional[str] = None


class ProductCreate(ProductBase):
    stock: Optional[List[str]] = Field(
        default=None, description="Optional initial stock lines for AUTO products"
    )


class ProductUpdate(BaseModel):
    category_id: Optional[int] = None
    sku: Optional[str] = None
    name_id: Optional[str] = None
    name_en: Optional[str] = None
    description_id: Optional[str] = None
    description_en: Optional[str] = None
    price: Optional[float] = None
    compare_price: Optional[float] = None
    currency: Optional[str] = None
    delivery_type: Optional[DeliveryType] = None
    image_url: Optional[str] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None
    delivery_instructions: Optional[str] = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sold_count: int = 0
    stock_available: int = 0
    stock_sold: int = 0
    category_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
