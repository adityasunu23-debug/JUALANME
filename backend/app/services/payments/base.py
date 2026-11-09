"""Payment provider contract and small shared helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from app.core.config import settings
from app.models.customer import Customer
from app.models.enums import PaymentStatus
from app.models.order import Order


@dataclass
class ProviderInvoice:
    """Normalised invoice data returned by any provider."""

    provider_invoice_id: Optional[str]
    status: str = PaymentStatus.PENDING.value
    provider_status: Optional[str] = None
    pay_address: Optional[str] = None
    pay_amount: Optional[float] = None
    payer_currency: Optional[str] = None
    payment_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    paid_amount: Optional[float] = None
    tx_hash: Optional[str] = None
    confirmations: int = 0
    expires_at: Optional[datetime] = None
    raw: Dict[str, Any] = field(default_factory=dict)


def callback_url(provider: str) -> str:
    return f"{settings.webhook_base_url.rstrip('/')}/api/v1/payments/webhook/{provider}"


def success_url(order_code: str) -> str:
    return f"{settings.dashboard_base_url.rstrip('/')}/pay/success?order={order_code}"


def md5_signature(payload: Any, api_key: str) -> str:
    """Cryptomus style signature: md5(base64(json) + api_key)."""
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    encoded = base64.b64encode(body.encode("utf-8")).decode("ascii")
    return hashlib.md5((encoded + api_key).encode("utf-8")).hexdigest()


def constant_time_equal(left: Optional[str], right: Optional[str]) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(str(left), str(right))


def normalize_status(raw_status: Optional[str], paid_amount: float, amount: float) -> str:
    """Map a gateway status string onto our PaymentStatus enum."""
    value = (raw_status or "").strip().lower()
    if value in ("paid", "paid_over", "confirmed", "completed", "success"):
        if value == "paid_over" or (paid_amount and paid_amount > amount + 0.000001):
            return PaymentStatus.OVERPAID.value
        return PaymentStatus.PAID.value
    if value in ("wrong_amount", "underpaid", "partially_paid"):
        return PaymentStatus.UNDERPAID.value
    if value in ("check", "confirming", "process", "processing", "pending_confirm"):
        return PaymentStatus.CONFIRMING.value
    if value in ("cancel", "cancelled", "canceled"):
        return PaymentStatus.CANCELLED.value
    if value in ("fail", "failed", "system_fail", "error"):
        return PaymentStatus.FAILED.value
    if value in ("expired", "timeout"):
        return PaymentStatus.EXPIRED.value
    return PaymentStatus.PENDING.value


NEW_INVOICE_STATUSES = (PaymentStatus.PENDING.value, PaymentStatus.CONFIRMING.value)
PAID_STATUSES = (PaymentStatus.PAID.value, PaymentStatus.OVERPAID.value)


class PaymentProvider(ABC):
    """Interface every crypto gateway adapter implements."""

    name: str = "base"

    @property
    @abstractmethod
    def configured(self) -> bool:
        """True when API credentials are present."""

    @abstractmethod
    async def create_invoice(self, order: Order, customer: Customer) -> ProviderInvoice:
        """Create an invoice for an order at the gateway."""

    @abstractmethod
    async def refresh_status(self, provider_invoice_id: str) -> ProviderInvoice:
        """Fetch the current invoice state from the gateway."""

    @abstractmethod
    def verify_webhook(
        self, headers: Mapping[str, str], payload: Dict[str, Any], raw_body: bytes
    ) -> bool:
        """Return True when the webhook signature is authentic."""

    def webhook_order_ref(self, payload: Dict[str, Any]) -> Optional[str]:
        return payload.get("order_id") or payload.get("order_ref")

    def webhook_invoice_id(self, payload: Dict[str, Any]) -> Optional[str]:
        return payload.get("uuid") or payload.get("invoice_id") or payload.get("txid")

    def provider_invoice(self, payload: Dict[str, Any]) -> ProviderInvoice:
        """Convert a webhook payload into a normalised invoice update."""
        amount = _to_float(payload.get("amount")) or 0.0
        paid = _to_float(
            payload.get("paid_amount")
            or payload.get("payer_amount")
            or payload.get("payment_amount")
        ) or 0.0
        raw_status = str(payload.get("status") or "")
        status = normalize_status(raw_status, paid or amount, amount)
        return ProviderInvoice(
            provider_invoice_id=self.webhook_invoice_id(payload),
            status=status,
            provider_status=raw_status or None,
            pay_address=payload.get("address") or payload.get("pay_address"),
            pay_amount=_to_float(payload.get("payer_amount"))
            or _to_float(payload.get("pay_amount")),
            payer_currency=payload.get("payer_currency"),
            payment_url=payload.get("url") or payload.get("payment_url"),
            paid_amount=paid or None,
            tx_hash=payload.get("txid") or payload.get("tx_hash"),
            confirmations=int(_to_float(payload.get("confirmations")) or 0),
            raw=payload,
        )


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
