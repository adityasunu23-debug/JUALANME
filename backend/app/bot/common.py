"""Rendering helpers shared by bot handlers."""
from __future__ import annotations

from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, Message

from app.bot.locales import translate
from app.bot.utils import (
    escape,
    format_amount,
    format_datetime,
    is_auto,
    localized_description,
    localized_name,
    qr_png,
    status_label,
    truncate,
)
from app.core.exceptions import AppError, NotFoundError, OutOfStock, ValidationError
from app.models.order import Order


async def safe_edit(message: Message, text: str, reply_markup=None) -> None:
    try:
        await message.edit_text(
            text, reply_markup=reply_markup, disable_web_page_preview=True
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        await message.answer(
            text, reply_markup=reply_markup, disable_web_page_preview=True
        )


def error_text(language: str, exc: Exception) -> str:
    if isinstance(exc, OutOfStock):
        return translate(language, "errors.stock")
    if isinstance(exc, ValidationError):
        return translate(language, "errors.validation", message=escape(exc.message))
    if isinstance(exc, NotFoundError):
        return translate(language, "errors.not_found")
    if isinstance(exc, AppError) and exc.code in ("payment_error", "provider_error"):
        return translate(language, "errors.provider")
    return translate(language, "errors.generic")


def product_text(product, language: str) -> str:
    lines = [f"<b>{escape(localized_name(product, language))}</b>", ""]
    description = localized_description(product, language)
    if description:
        lines.extend([escape(truncate(description, 600)), ""])
    lines.append(translate(language, "product.price", price=format_amount(product.price, product.currency)))
    if is_auto(product):
        lines.append(translate(language, "product.stock", stock=product.stock_available))
        lines.append(translate(language, "product.delivery_auto"))
    else:
        lines.append(translate(language, "product.delivery_manual"))
    return "\n".join(lines)


def quantity_text(product, quantity: int, language: str) -> str:
    return "\n".join(
        [
            translate(language, "qty.title", name=escape(localized_name(product, language)),
                      price=format_amount(product.price, product.currency),
                      stock=product.stock_available),
            "",
            translate(language, "qty.total", total=format_amount(float(product.price) * quantity, product.currency)),
        ]
    )


def checkout_text(
    product,
    quantity: int,
    language: str,
    voucher_code: Optional[str] = None,
    discount: float = 0.0,
) -> str:
    subtotal = round(float(product.price) * quantity, 6)
    total = max(subtotal - discount, 0.0)
    lines = [
        translate(language, "checkout.title"),
        "",
        f"• {escape(localized_name(product, language))} x{quantity}",
        translate(language, "checkout.subtotal", amount=format_amount(subtotal, product.currency)),
    ]
    if voucher_code:
        lines.append(
            translate(language, "checkout.discount", code=escape(voucher_code), amount=format_amount(discount, product.currency))
        )
    lines.extend(
        [
            translate(language, "checkout.total", amount=format_amount(total, product.currency)),
            translate(language, "checkout.payment_note"),
        ]
    )
    if voucher_code:
        lines.append(translate(language, "checkout.voucher_applied", code=escape(voucher_code)))
    else:
        lines.append(translate(language, "checkout.voucher_hint"))
    return "\n".join(lines)


def order_text(order: Order, language: str) -> str:
    lines = [
        translate(language, "order.title"),
        "",
        translate(language, "invoice.order", code=escape(order.order_code)),
        translate(language, "order.status", status=status_label(order.status, language)),
        translate(language, "order.product", name=escape(order.product_name), qty=order.quantity),
        translate(language, "order.total", amount=format_amount(float(order.total_amount), order.currency)),
        translate(language, "order.date", date=format_datetime(order.created_at)),
    ]
    if order.voucher_code:
        lines.append(
            translate(language, "checkout.discount", code=escape(order.voucher_code), amount=format_amount(float(order.discount_amount), order.currency))
        )
    if order.status in ("PAID", "DELIVERED", "COMPLETED"):
        lines.append(
            translate(language, "order.delivery", status=status_label(order.delivery_status, language))
        )
    return "\n".join(lines)


def invoice_text(order: Order, language: str) -> str:
    invoice = order.active_invoice
    lines = [
        translate(language, "invoice.title"),
        "",
        translate(language, "invoice.order", code=escape(order.order_code)),
        translate(language, "invoice.product", name=escape(order.product_name), qty=order.quantity),
        translate(language, "invoice.total", amount=format_amount(float(order.total_amount), order.currency)),
        translate(language, "invoice.network"),
    ]
    if invoice is not None:
        if invoice.network:
            lines[-1] = f"Network: {escape(invoice.network.upper())}" if language == "en" else f"Jaringan: {escape(invoice.network.upper())}"
        if invoice.pay_address:
            lines.extend(["", translate(language, "invoice.address", address=escape(invoice.pay_address))])
        if invoice.expires_at:
            lines.append(translate(language, "invoice.expires", expires=format_datetime(invoice.expires_at)))
        if invoice.status:
            lines.append(
                translate(language, "invoice.status", status=status_label(invoice.status, language))
            )
    return "\n".join(lines)


async def send_invoice(
    bot: Bot, chat_id: int, order: Order, language: str, reply_markup=None
) -> None:
    caption = invoice_text(order, language)
    invoice = order.active_invoice
    qr_target = None
    if invoice is not None:
        qr_target = invoice.payment_url or invoice.pay_address
    image = qr_png(qr_target) if qr_target else None
    if image:
        await bot.send_photo(
            chat_id,
            BufferedInputFile(image, filename="invoice.png"),
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    else:
        await bot.send_message(
            chat_id, caption, parse_mode="HTML", reply_markup=reply_markup
        )
