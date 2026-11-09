"""Catalogue browsing and checkout flow."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.common import (
    checkout_text,
    error_text,
    product_text,
    quantity_text,
    safe_edit,
    send_invoice,
)
from app.bot.locales import translate
from app.core.exceptions import AppError
from app.models.customer import Customer
from app.services import catalog_service, order_service, voucher_service

router = Router(name="catalog")


class CheckoutStates(StatesGroup):
    voucher = State()


def _parse(data: str) -> list[str]:
    return (data or "").split(":")


@router.callback_query(F.data == "menu:catalog")
async def cb_catalog(callback: CallbackQuery, session, lang: str) -> None:
    await callback.answer()
    categories = await catalog_service.list_categories(session, active_only=True)
    if not categories:
        if callback.message is not None:
            await safe_edit(
                callback.message,
                translate(lang, "catalog.empty"),
                keyboards.back_keyboard(lang),
            )
        return
    if callback.message is not None:
        await safe_edit(
            callback.message,
            translate(lang, "catalog.title"),
            keyboards.categories_keyboard(categories, lang),
        )


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery, session, lang: str) -> None:
    parts = _parse(callback.data or "")
    try:
        category_id = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer(translate(lang, "errors.not_found"), show_alert=True)
        return
    await callback.answer()
    category = await catalog_service.get_category(session, category_id)
    products, _ = await catalog_service.list_products(
        session, category_id=category_id, active_only=True, page_size=50
    )
    text = (
        translate(lang, "catalog.title_category", category=category.name_for(lang))
        if products
        else translate(lang, "catalog.product_empty")
    )
    if callback.message is not None:
        await safe_edit(
            callback.message,
            text,
            keyboards.products_keyboard(products, category_id, lang),
        )


@router.callback_query(F.data.startswith("prod:"))
async def cb_product(callback: CallbackQuery, session, lang: str) -> None:
    parts = _parse(callback.data or "")
    try:
        product = await catalog_service.get_product(session, int(parts[1]))
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "product.not_found"), show_alert=True)
        return
    if not product.is_active:
        await callback.answer(translate(lang, "product.not_found"), show_alert=True)
        return
    output = await catalog_service.product_out(session, product)
    await callback.answer()
    text = product_text(output, lang)
    markup = keyboards.product_keyboard(output, lang)
    if callback.message is None:
        return
    if output.image_url:
        await callback.message.answer_photo(
            output.image_url, caption=text, reply_markup=markup
        )
    else:
        await safe_edit(callback.message, text, markup)


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery, session, lang: str) -> None:
    parts = _parse(callback.data or "")
    try:
        product = await catalog_service.product_out(
            session, await catalog_service.get_product(session, int(parts[1]))
        )
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "product.not_found"), show_alert=True)
        return
    if product.delivery_type.value == "AUTO" and product.stock_available <= 0:
        await callback.answer(translate(lang, "product.out_of_stock"), show_alert=True)
        return
    quantity = max(1, product.min_quantity)
    await callback.answer()
    if callback.message is not None:
        await safe_edit(
            callback.message,
            quantity_text(product, quantity, lang),
            keyboards.quantity_keyboard(product, quantity, lang),
        )


@router.callback_query(F.data.startswith("qty:"))
async def cb_quantity(callback: CallbackQuery, session, lang: str) -> None:
    parts = _parse(callback.data or "")
    try:
        product = await catalog_service.product_out(
            session, await catalog_service.get_product(session, int(parts[1]))
        )
        quantity = int(parts[2])
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "product.not_found"), show_alert=True)
        return
    quantity = max(product.min_quantity, min(quantity, product.max_quantity))
    if product.delivery_type.value == "AUTO":
        quantity = min(quantity, max(product.stock_available, product.min_quantity))
    await callback.answer()
    if callback.message is not None:
        await safe_edit(
            callback.message,
            quantity_text(product, quantity, lang),
            keyboards.quantity_keyboard(product, quantity, lang),
        )


@router.callback_query(F.data.startswith("checkout:"))
async def cb_checkout(callback: CallbackQuery, session, lang: str) -> None:
    parts = _parse(callback.data or "")
    try:
        product = await catalog_service.product_out(
            session, await catalog_service.get_product(session, int(parts[1]))
        )
        quantity = int(parts[2])
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "product.not_found"), show_alert=True)
        return
    await callback.answer()
    if callback.message is not None:
        await safe_edit(
            callback.message,
            checkout_text(product, quantity, lang),
            keyboards.checkout_keyboard(product.id, quantity, lang),
        )


@router.callback_query(F.data.startswith("vouch:"))
async def cb_voucher_prompt(
    callback: CallbackQuery, state: FSMContext, session, lang: str
) -> None:
    parts = _parse(callback.data or "")
    try:
        product_id, quantity = int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        await callback.answer(translate(lang, "errors.generic"), show_alert=True)
        return
    await state.set_state(CheckoutStates.voucher)
    await state.update_data(product_id=product_id, quantity=quantity)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(
            translate(lang, "voucher.prompt"),
            reply_markup=keyboards.back_keyboard(lang, f"checkout:{product_id}:{quantity}"),
        )


@router.message(CheckoutStates.voucher)
async def cb_voucher_input(
    message: Message, state: FSMContext, session, customer: Customer, lang: str
) -> None:
    data = await state.get_data()
    product_id = int(data.get("product_id") or 0)
    quantity = int(data.get("quantity") or 1)
    code = (message.text or "").strip().upper()
    if not code:
        await message.answer(translate(lang, "voucher.prompt"))
        return
    try:
        product = await catalog_service.product_out(
            session, await catalog_service.get_product(session, product_id)
        )
    except AppError:
        await state.clear()
        await message.answer(translate(lang, "product.not_found"))
        return
    subtotal = round(float(product.price) * quantity, 6)
    try:
        voucher, discount = await voucher_service.validate_voucher(
            session, code, subtotal, customer.id
        )
    except voucher_service.VoucherError as exc:
        await message.answer(translate(lang, "voucher.invalid", reason=str(exc)))
        return
    await state.clear()
    await message.answer(
        checkout_text(product, quantity, lang, voucher.code, discount),
        reply_markup=keyboards.checkout_keyboard(product.id, quantity, lang, voucher.code),
    )


@router.callback_query(F.data.startswith("pay:"))
async def cb_pay(
    callback: CallbackQuery, bot: Bot, session, customer: Customer, lang: str
) -> None:
    parts = _parse(callback.data or "")
    try:
        product_id, quantity = int(parts[1]), int(parts[2])
        voucher_code = parts[3] if len(parts) > 3 and parts[3] else None
    except (IndexError, ValueError):
        await callback.answer(translate(lang, "errors.generic"), show_alert=True)
        return
    if callback.message is None:
        await callback.answer()
        return
    try:
        product = await catalog_service.get_product(session, product_id)
        order = await order_service.create_order(
            session,
            customer,
            product,
            quantity,
            voucher_code=voucher_code,
            language=lang,
        )
    except AppError as exc:
        await callback.answer(error_text(lang, exc), show_alert=True)
        return
    except Exception:
        await callback.answer(translate(lang, "errors.generic"), show_alert=True)
        return
    await callback.answer()
    await send_invoice(
        bot,
        callback.message.chat.id,
        order,
        lang,
        keyboards.invoice_keyboard(order, lang),
    )
