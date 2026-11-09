"""Deterministic mock gateway used for local development and tests."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping

from app.core.config import settings
from app.models.customer import Customer
from app.models.order import Order
from app.services.payments.base import (
    PaymentProvider,
    ProviderInvoice,
    normalize_status,
)


class MockProvider(PaymentProvider):
    """Accepts any webhook and exposes a manual "pay" link for testing."""

    name = "mock"

    @property
    def configured(self) -> bool:
        return True

    def _address(self, order_code: str) -> str:
        digest = hashlib.sha256(order_code.encode("utf-8")).hexdigest()
        return "0x" + digest[:40]

    async def create_invoice(self, order: Order, customer: Customer) -> ProviderInvoice:
        invoice_id = f"mock-{order.order_code.lower()}"
        base = settings.webhook_base_url.rstrip("/")
        return ProviderInvoice(
            provider_invoice_id=invoice_id,
            status="PENDING",
            provider_status="unpaid",
            pay_address=self._address(order.order_code),
            pay_amount=float(order.total_amount),
            payer_currency=settings.payment_currency,
            payment_url=f"{base}/api/v1/payments/mock/{order.order_code}/pay",
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.invoice_lifetime_minutes),
            raw={"mock": True, "order_id": order.order_code},
        )

    async def refresh_status(self, provider_invoice_id: str) -> ProviderInvoice:
        return ProviderInvoice(
            provider_invoice_id=provider_invoice_id,
            status="",
            provider_status="unchanged",
        )

    def verify_webhook(
        self, headers: Mapping[str, str], payload: Dict[str, Any], raw_body: bytes
    ) -> bool:
        return True

    def provider_invoice(self, payload: Dict[str, Any]) -> ProviderInvoice:
        order_ref = payload.get("order_id", "")
        invoice_id = payload.get("uuid") or (
            f"mock-{order_ref.lower()}" if order_ref else None
        )
        raw_status = str(payload.get("status") or "paid")
        amount = float(payload.get("amount") or 0)
        paid = float(
            payload.get("payer_amount")
            or payload.get("paid_amount")
            or payload.get("amount")
            or 0
        )
        return ProviderInvoice(
            provider_invoice_id=invoice_id,
            status=normalize_status(raw_status, paid, amount),
            provider_status=raw_status,
            pay_address=payload.get("address") or self._address(order_ref),
            pay_amount=payload.get("payer_amount"),
            paid_amount=paid or None,
            tx_hash=payload.get("txid")
            or ("0x" + hashlib.sha256(order_ref.encode()).hexdigest()),
            raw=payload,
        )
