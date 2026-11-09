"""Voucher and broadcast schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BroadcastAudience, VoucherType


class VoucherBase(BaseModel):
    code: str = Field(..., max_length=32)
    description: Optional[str] = None
    type: VoucherType = VoucherType.PERCENT
    value: float = Field(..., gt=0)
    min_purchase: float = 0
    max_discount: Optional[float] = None
    usage_limit: int = 0
    per_customer_limit: int = 1
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True


class VoucherCreate(VoucherBase):
    pass


class VoucherUpdate(BaseModel):
    description: Optional[str] = None
    type: Optional[VoucherType] = None
    value: Optional[float] = None
    min_purchase: Optional[float] = None
    max_discount: Optional[float] = None
    usage_limit: Optional[int] = None
    per_customer_limit: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class VoucherOut(VoucherBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    used_count: int = 0
    created_at: Optional[datetime] = None


class VoucherValidateRequest(BaseModel):
    code: str
    subtotal: float


class VoucherValidateResponse(BaseModel):
    valid: bool
    discount: float = 0
    total: float = 0
    message: str = ""


class BroadcastBase(BaseModel):
    title: str = Field(..., max_length=160)
    message: str
    audience: BroadcastAudience = BroadcastAudience.ALL


class BroadcastCreate(BroadcastBase):
    send_now: bool = False


class BroadcastOut(BroadcastBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_recipients: int = 0
    sent_count: int = 0
    failed_count: int = 0
    created_by_admin_id: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
