"""Cryptomus (formerly Payerly) payment gateway adapter.

Docs: https://doc.cryptomus.com/

Signatures
----------
Request:  md5( base64( json_body ) + api_key )  -> sent in the ``sign`` header
Webhook:  md5( base64( json_body_without_sign ) + api_key ) -> ``sign`` field
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

import httpx

from app.core.config import settings
from app.models.customer import Customer
from app.models.enums import PaymentStatus
from app.models.order import Order
from app.services.payments.base import (
    PaymentProvider,
    ProviderInvoice,
    callback_url,
    constant_time_equal,
    md5_signature,
    normalize_status,
    success_url,
)

logger = logging.getLogger(__name__)


class CryptomusError(Exception):
    """Raised when the gateway rejects a request."""


class CryptomusProvider(PaymentProvider):
    name = "cryptomus"

    def __init__(
        self,
        merchant_uuid: Optional[str] = None,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        # Credentials come from the values synced into runtime settings,
        # which the dashboard can update without a redeploy.
        self.merchant_uuid = merchant_uuid or settings.cryptomus_merchant_uuid
        self.api_key = api_key or settings.cryptomus_api_key
        self.api_url = (api_url or settings.cryptomus_api_url).rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.merchant_uuid and self.api_key)

    async def _request(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.configured:
            raise CryptomusError("Kredensial Cryptomus belum dikonfigurasi")
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        headers = {
            "merchant": self.merchant_uuid,
            "sign": md5_signature(payload, self.api_key),
            "Content-Type": "application/json",
        }
        url = f"{self.api_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, content=body, headers=headers)
        except httpx.HTTPError as exc:
            raise CryptomusError(f"Gagal menghubungi Cryptomus: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise CryptomusError(
                f"Respons Cryptomus tidak valid (HTTP {response.status_code})"
            ) from exc

        if response.status_code >= 400 or data.get("state") not in (0, "0"):
            message = data.get("message") or data.get("errors") or "permintaan ditolak"
            raise CryptomusError(f"Cryptomus HTTP {response.status_code}: {message}")
        result = data.get("result")
        if not isinstance(result, dict):
            raise CryptomusError("Cryptomus tidak mengembalikan data invoice")
        return result

    async def create_invoice(self, order: Order, customer: Customer) -> ProviderInvoice:
        payload: Dict[str, Any] = {
            "amount": f"{float(order.total_amount):.2f}",
            "currency": settings.payment_currency,
            "network": settings.cryptomus_network,
            "order_id": order.order_code,
            "url_callback": callback_url(self.name),
            "url_return": success_url(order.order_code),
            "url_success": success_url(order.order_code),
            "lifetime": settings.invoice_lifetime_minutes * 60,
            "additional_data": str(customer.telegram_id),
            "is_payment_multiple": True,
            "subtract": 0,
        }
        result = await self._request("/payment", payload)
        return self._to_invoice(result, order)

    async def refresh_status(self, provider_invoice_id: str) -> ProviderInvoice:
        result = await self._request("/payment/status", {"uuid": provider_invoice_id})
        return self._to_invoice(result, None)

    def _to_invoice(
        self, result: Dict[str, Any], order: Optional[Order]
    ) -> ProviderInvoice:
        raw_status = str(
            result.get("payment_status") or result.get("status") or "unpaid"
        )
        amount = _float(result.get("amount")) or (
            float(order.total_amount) if order else 0.0
        )
        paid_amount = _float(result.get("payer_amount"))
        normalized = normalize_status(raw_status, paid_amount or 0.0, amount)
        expires_at = _parse_datetime(result.get("expired_at"))
        return ProviderInvoice(
            provider_invoice_id=result.get("uuid") or result.get("txid"),
            status=normalized,
            provider_status=raw_status,
            pay_address=result.get("address"),
            pay_amount=_float(result.get("payer_amount")),
            payer_currency=result.get("payer_currency"),
            payment_url=result.get("url"),
            paid_amount=paid_amount,
            tx_hash=result.get("txid"),
            expires_at=expires_at,
            raw=result,
        )

    def verify_webhook(
        self, headers: Mapping[str, str], payload: Dict[str, Any], raw_body: bytes
    ) -> bool:
        if not self.api_key:
            return False
        received = str(payload.get("sign") or headers.get("sign") or "")
        if not received:
            return False

        body_without_sign = {key: value for key, value in payload.items() if key != "sign"}
        candidates = {
            md5_signature(body_without_sign, self.api_key),
            md5_signature(dict(sorted(body_without_sign.items())), self.api_key),
        }
        try:
            body_text = raw_body.decode("utf-8") if raw_body else ""
            parsed = json.loads(body_text) if body_text else {}
            if isinstance(parsed, dict):
                parsed.pop("sign", None)
                candidates.add(md5_signature(parsed, self.api_key))
        except (ValueError, UnicodeDecodeError):
            pass
        return any(constant_time_equal(candidate, received) for candidate in candidates)


def _float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value).replace("T", " ").replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
