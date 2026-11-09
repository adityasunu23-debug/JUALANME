"""Payment gateway schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class PaymentInvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    order_code: Optional[str] = None
    provider: str
    provider_invoice_id: Optional[str] = None
    provider_order_ref: str
    amount: float
    paid_amount: Optional[float] = None
    currency: str
    network: str
    pay_address: Optional[str] = None
    pay_amount: Optional[float] = None
    payer_currency: Optional[str] = None
    qr_code_url: Optional[str] = None
    payment_url: Optional[str] = None
    status: str
    provider_status: Optional[str] = None
    tx_hash: Optional[str] = None
    confirmations: int = 0
    is_manual: bool = False
    expires_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class WebhookEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    event_type: Optional[str] = None
    signature_valid: bool
    processed: bool
    order_code: Optional[str] = None
    provider_invoice_id: Optional[str] = None
    error: Optional[str] = None
    source_ip: Optional[str] = None
    created_at: Optional[datetime] = None


class ProviderStatus(BaseModel):
    provider: str
    configured: bool
    merchant_uuid_set: bool = False
    api_key_set: bool = False
    network: str = "bep20"
    currency: str = "USDT"
    webhook_url: Optional[str] = None
    supported_networks: List[str] = []
    notes: Optional[str] = None


class ProviderCheckResponse(BaseModel):
    provider: str
    reachable: bool
    usdt_bep20_supported: bool
    detail: str
    raw: Optional[Dict[str, Any]] = None


class ManualPaymentRequest(BaseModel):
    tx_hash: Optional[str] = None
    note: Optional[str] = None
    paid_amount: Optional[float] = None


class WebhookAck(BaseModel):
    status: str = "ok"
    detail: Optional[str] = None
