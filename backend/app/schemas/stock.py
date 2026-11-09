"""Stock management schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StockItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    content: str
    label: Optional[str] = None
    is_used: bool
    order_id: Optional[int] = None
    used_at: Optional[datetime] = None
    source: str = "manual"
    created_at: Optional[datetime] = None


class StockItemCreate(BaseModel):
    product_id: int
    content: str
    label: Optional[str] = None


class StockBulkCreate(BaseModel):
    product_id: int
    lines: List[str] = Field(default_factory=list, description="One deliverable per line")
    label: Optional[str] = None
    deduplicate: bool = True


class StockImportResult(BaseModel):
    imported: int = 0
    skipped: int = 0
    duplicates: int = 0
    invalid: int = 0
    batch_id: Optional[str] = None
    message: str = ""


class StockSummary(BaseModel):
    product_id: int
    product_name: str
    delivery_type: str
    available: int = 0
    sold: int = 0
    total: int = 0
    low_stock: bool = False


class StockUpdate(BaseModel):
    content: Optional[str] = None
    label: Optional[str] = None
