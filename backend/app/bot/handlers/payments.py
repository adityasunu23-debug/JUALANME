"""Payment status checks from the invoice message."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from app.bot import keyboards
from app.bot.common import error_text, invoice_text, order_text
from app.bot.locales import translate
from app.bot.utils import status_label
from app.core.exceptions import AppError
from app.models.customer import Customer
from app.services import order_service
from app.services import payments as payment_service

router = Router(name="payments")


async def _update_message(callback: CallbackQuery, text: str, markup) -> None:
    message = callback.message
    if message is None:
        return
    if message.photo:
        try:
            await message.edit_caption(caption=text, reply_markup=markup)
            return
        except Exception:
            pass
    try:
        await message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except Exception:
        await message.answer(text, reply_markup=markup, disable_web_page_preview=True)


@router.callback_query(F.data.startswith("check:"))
async def cb_check_payment(
    callback: CallbackQuery, bot: Bot, session, customer: Customer, lang: str
) -> None:
    try:
        order = await order_service.get_order(session, int((callback.data or "").split(":")[1]))
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "errors.not_found"), show_alert=True)
        return
    if order.customer_id != customer.id:
        await callback.answer(translate(lang, "errors.not_found"), show_alert=True)
        return

    invoice = order.active_invoice
    if invoice is not None and not order.is_paid and invoice.status in (
        "PENDING",
        "CONFIRMING",
    ):
        try:
            await payment_service.refresh_invoice(session, invoice)
        except Exception:
            pass

    if order.is_paid:
        delivery = order.delivery
        delivered = delivery is not None and delivery.delivered_content
        if delivered:
            text = "\n\n".join(
                [
                    order_text(order, lang),
                    translate(lang, "invoice.paid"),
                    translate(lang, "order.delivery", status=status_label(order.delivery_status, lang)),
                ]
            )
            await callback.answer(translate(lang, "invoice.paid"))
            await _update_message(callback, text, keyboards.order_keyboard(order, lang))
        else:
            text = "\n\n".join([order_text(order, lang), translate(lang, "invoice.manual_wait")])
            await callback.answer(translate(lang, "invoice.paid"))
            await _update_message(callback, text, keyboards.order_keyboard(order, lang))
        return

    if order.status in ("EXPIRED", "CANCELLED", "FAILED"):
        await callback.answer(translate(lang, "invoice.expired"))
        text = "\n\n".join(
            [
                invoice_text(order, lang),
                translate(
                    lang,
                    "invoice.expired" if order.status == "EXPIRED" else "invoice.cancelled",
                ),
            ]
        )
        await _update_message(callback, text, keyboards.order_keyboard(order, lang))
        return

    await callback.answer(translate(lang, "invoice.not_paid_yet"))
    await _update_message(
        callback,
        "\n\n".join([invoice_text(order, lang), translate(lang, "invoice.not_paid_yet")]),
        keyboards.invoice_keyboard(order, lang),
    )
