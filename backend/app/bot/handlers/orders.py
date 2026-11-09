"""Order history and delivered content."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.common import error_text, order_text, safe_edit
from app.bot.locales import translate
from app.bot.utils import escape
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.customer import Customer
from app.services import order_service

router = Router(name="orders")


async def _own_order(session, order_id: int, customer: Customer):
    order = await order_service.get_order(session, order_id)
    if order.customer_id != customer.id:
        raise NotFoundError("Pesanan tidak ditemukan")
    return order


@router.message(Command("orders"))
async def cmd_orders(message: Message, session, customer: Customer, lang: str) -> None:
    orders = await order_service.customer_orders(session, customer.id, limit=10)
    if not orders:
        await message.answer(
            translate(lang, "orders.empty"),
            reply_markup=keyboards.back_keyboard(lang),
        )
        return
    await message.answer(
        translate(lang, "orders.title"), reply_markup=keyboards.orders_keyboard(orders, lang)
    )


@router.callback_query(F.data == "menu:orders")
async def cb_orders(callback: CallbackQuery, session, customer: Customer, lang: str) -> None:
    await callback.answer()
    orders = await order_service.customer_orders(session, customer.id, limit=10)
    if callback.message is None:
        return
    if not orders:
        await safe_edit(
            callback.message,
            translate(lang, "orders.empty"),
            keyboards.back_keyboard(lang),
        )
        return
    await safe_edit(
        callback.message,
        translate(lang, "orders.title"),
        keyboards.orders_keyboard(orders, lang),
    )


@router.callback_query(F.data.startswith("order:"))
async def cb_order_detail(
    callback: CallbackQuery, session, customer: Customer, lang: str
) -> None:
    try:
        order = await _own_order(session, int((callback.data or "").split(":")[1]), customer)
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "errors.not_found"), show_alert=True)
        return
    await callback.answer()
    if callback.message is not None:
        await safe_edit(
            callback.message, order_text(order, lang), keyboards.order_keyboard(order, lang)
        )


@router.callback_query(F.data.startswith("content:"))
async def cb_order_content(
    callback: CallbackQuery, session, customer: Customer, lang: str
) -> None:
    try:
        order = await _own_order(session, int((callback.data or "").split(":")[1]), customer)
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "errors.not_found"), show_alert=True)
        return
    delivery = order.delivery
    if delivery is None or not delivery.delivered_content:
        await callback.answer(translate(lang, "order.content_missing"), show_alert=True)
        return
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(
            translate(
                lang,
                "order.content_title",
                code=escape(order.order_code),
                content=escape(delivery.delivered_content),
            )
        )


@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel_order(
    callback: CallbackQuery, session, customer: Customer, lang: str
) -> None:
    try:
        order = await _own_order(session, int((callback.data or "").split(":")[1]), customer)
        await order_service.cancel_order(session, order, reason="Dibatalkan oleh pelanggan")
    except ConflictError as exc:
        await callback.answer(error_text(lang, exc), show_alert=True)
        return
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "errors.not_found"), show_alert=True)
        return
    await callback.answer(translate(lang, "invoice.cancel_ok"))
    if callback.message is not None:
        await safe_edit(
            callback.message,
            order_text(order, lang),
            keyboards.order_keyboard(order, lang),
        )
