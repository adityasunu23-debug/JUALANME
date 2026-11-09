"""Shared formatting helpers for the Telegram bot."""
from __future__ import annotations

import html
import io
from datetime import datetime, timezone
from typing import Optional

try:  # optional dependency, imported lazily by the invoice renderer
    import qrcode
except Exception:  # pragma: no cover
    qrcode = None  # type: ignore[assignment]

STATUS_LABELS = {
    "id": {
        "PENDING_PAYMENT": "Menunggu Pembayaran",
        "PAID": "Dibayar",
        "DELIVERED": "Terkirim",
        "COMPLETED": "Selesai",
        "EXPIRED": "Kedaluwarsa",
        "CANCELLED": "Dibatalkan",
        "FAILED": "Gagal",
        "REFUNDED": "Dikembalikan",
        "PENDING": "Menunggu",
        "PROCESSING": "Diproses",
        "NOT_REQUIRED": "Tidak diperlukan",
    },
    "en": {
        "PENDING_PAYMENT": "Awaiting Payment",
        "PAID": "Paid",
        "DELIVERED": "Delivered",
        "COMPLETED": "Completed",
        "EXPIRED": "Expired",
        "CANCELLED": "Cancelled",
        "FAILED": "Failed",
        "REFUNDED": "Refunded",
        "PENDING": "Pending",
        "PROCESSING": "Processing",
        "NOT_REQUIRED": "Not required",
    },
}

OPEN_ORDER_STATUSES = {"PENDING_PAYMENT"}
PAID_ORDER_STATUSES = {"PAID", "DELIVERED", "COMPLETED"}


def status_label(status: str, language: str = "id") -> str:
    table = STATUS_LABELS.get(language, STATUS_LABELS["id"])
    return table.get(status, status.replace("_", " ").title())


def format_amount(value: float, currency: str = "USDT") -> str:
    try:
        return f"{float(value):,.2f} {currency}"
    except (TypeError, ValueError):
        return f"0.00 {currency}"


def format_datetime(value: Optional[datetime]) -> str:
    if value is None:
        return "-"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%Y-%m-%d %H:%M")


def escape(value: Optional[str]) -> str:
    return html.escape(value or "", quote=False)


def truncate(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def qr_png(data: str) -> Optional[bytes]:
    if qrcode is None or not data:
        return None
    try:
        image = qrcode.make(data)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:  # pragma: no cover - rendering must never break a sale
        return None


def product_available(product) -> int:
    return int(getattr(product, "stock_available", 0) or 0)


def localized_name(obj, language: str = "id") -> str:
    getter = getattr(obj, "name_for", None)
    if callable(getter):
        try:
            return str(getter(language))
        except Exception:
            pass
    value = getattr(obj, "name_en" if language == "en" else "name_id", None)
    return str(value or getattr(obj, "name_id", "") or getattr(obj, "name", "") or "")


def localized_description(obj, language: str = "id") -> str:
    getter = getattr(obj, "description_for", None)
    if callable(getter):
        try:
            return str(getter(language) or "")
        except Exception:
            pass
    value = getattr(obj, "description_en" if language == "en" else "description_id", None)
    return str(value or "")


def is_auto(product) -> bool:
    value = getattr(product, "delivery_type", None)
    return str(getattr(value, "value", value) or "").upper() == "AUTO"
