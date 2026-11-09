"""Low level Telegram Bot API notifications used by services and workers.

The bot package uses aiogram for interactive conversations, but outbound
notifications from the API layer go through this small httpx client so a
webhook-only deployment does not need a running bot instance.
"""
import html
import logging
from typing import Iterable, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"


def escape(value: Optional[str]) -> str:
    return html.escape(value or "", quote=False)


def is_configured() -> bool:
    return bool(settings.bot_token)


async def send_message(
    chat_id: int | str,
    text: str,
    *,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
    reply_markup: Optional[dict] = None,
) -> bool:
    """Send one message. Returns False instead of raising on transport errors."""
    if not settings.bot_token or not chat_id:
        return False
    payload: dict = {
        "chat_id": chat_id,
        "text": text[:4096],
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    url = f"{API_BASE}/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.warning("Telegram sendMessage failed: %s", response.text[:300])
                return False
            return True
    except httpx.HTTPError as exc:
        logger.warning("Telegram sendMessage error: %s", exc)
        return False


async def notify_admins(text: str, *, parse_mode: str = "HTML") -> int:
    """Broadcast a message to every configured admin telegram id."""
    sent = 0
    for admin_id in _admin_ids():
        if await send_message(admin_id, text, parse_mode=parse_mode):
            sent += 1
    return sent


def _admin_ids() -> Iterable[int]:
    return settings.admin_telegram_id_list


def order_paid_text(
    order_code: str,
    product_name: str,
    quantity: int,
    total: float,
    currency: str,
    language: str = "id",
) -> str:
    if language == "en":
        return (
            "<b>Payment received</b>\n"
            f"Order: <code>{escape(order_code)}</code>\n"
            f"Product: {escape(product_name)} x{quantity}\n"
            f"Total: {total:.2f} {escape(currency)}\n\n"
            "Your product will be delivered automatically in a moment."
        )
    return (
        "<b>Pembayaran diterima</b>\n"
        f"Pesanan: <code>{escape(order_code)}</code>\n"
        f"Produk: {escape(product_name)} x{quantity}\n"
        f"Total: {total:.2f} {escape(currency)}\n\n"
        "Produk Anda akan segera dikirim otomatis."
    )


def order_delivered_text(
    order_code: str,
    product_name: str,
    content: str,
    language: str = "id",
) -> str:
    safe_content = escape(content)
    if language == "en":
        return (
            "<b>Order delivered</b>\n"
            f"Order: <code>{escape(order_code)}</code>\n"
            f"Product: {escape(product_name)}\n\n"
            f"<b>Your item(s):</b>\n<pre>{safe_content}</pre>\n\n"
            "Thank you for shopping with us!"
        )
    return (
        "<b>Pesanan telah dikirim</b>\n"
        f"Pesanan: <code>{escape(order_code)}</code>\n"
        f"Produk: {escape(product_name)}\n\n"
        f"<b>Produk Anda:</b>\n<pre>{safe_content}</pre>\n\n"
        "Terima kasih telah berbelanja!"
    )


def admin_new_order_text(
    order_code: str,
    product_name: str,
    quantity: int,
    total: float,
    currency: str,
    delivery_type: str,
    customer_name: str,
) -> str:
    return (
        "<b>Pesanan baru dibayar</b>\n"
        f"Kode: <code>{escape(order_code)}</code>\n"
        f"Pelanggan: {escape(customer_name)}\n"
        f"Produk: {escape(product_name)} x{quantity}\n"
        f"Total: {total:.2f} {escape(currency)}\n"
        f"Pengiriman: {escape(delivery_type)}"
    )


def manual_delivery_needed_text(
    order_code: str,
    product_name: str,
    quantity: int,
    customer_name: str,
) -> str:
    return (
        "<b>Perlu pengiriman manual</b>\n"
        f"Kode: <code>{escape(order_code)}</code>\n"
        f"Pelanggan: {escape(customer_name)}\n"
        f"Produk: {escape(product_name)} x{quantity}\n"
        "Buka dashboard untuk memproses pesanan ini."
    )
