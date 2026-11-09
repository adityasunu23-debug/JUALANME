"""Support tickets created and answered from the bot."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.common import safe_edit
from app.bot.locales import translate
from app.bot.utils import escape, format_datetime, status_label, truncate
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.config import settings
from app.models.customer import Customer
from app.services import telegram_notify, ticket_service
from app.models.enums import SenderType

router = Router(name="support")


class SupportStates(StatesGroup):
    subject = State()
    message = State()
    reply = State()


def _menu_text(lang: str) -> str:
    return translate(lang, "support.menu")


async def _show_ticket(session, ticket_id: int, customer: Customer, lang: str) -> str:
    ticket = await ticket_service.get_ticket(session, ticket_id)
    if ticket.customer_id != customer.id:
        raise NotFoundError("Tiket tidak ditemukan")
    messages = list(ticket.messages or [])[-10:]
    lines = [
        translate(
            lang,
            "support.thread_title",
            code=escape(ticket.ticket_code),
            status=status_label(ticket.status, lang),
            subtitle=escape(truncate(ticket.subject, 120)),
        )
    ]
    for entry in messages:
        who = "👤 Support" if entry.sender_type == SenderType.ADMIN.value else "🧑 Anda" if lang == "id" else "🧑 You"
        lines.extend(
            [
                "",
                f"{who} • {format_datetime(entry.created_at)}",
                escape(truncate(entry.message, 800)),
            ]
        )
    return "\n".join(lines)


@router.message(Command("support"))
async def cmd_support(message: Message, lang: str) -> None:
    await message.answer(
        _menu_text(lang),
        reply_markup=keyboards.support_keyboard(lang, settings.support_username),
    )


@router.callback_query(F.data == "menu:support")
async def cb_support_menu(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
    if callback.message is not None:
        await safe_edit(
            callback.message,
            _menu_text(lang),
            keyboards.support_keyboard(lang, settings.support_username),
        )


@router.callback_query(F.data == "support:new")
async def cb_support_new(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.set_state(SupportStates.subject)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(
            translate(lang, "support.subject_prompt"),
            reply_markup=keyboards.back_keyboard(lang, "menu:support"),
        )


@router.message(SupportStates.subject)
async def msg_support_subject(message: Message, state: FSMContext, lang: str) -> None:
    subject = (message.text or "").strip()
    if not subject:
        await message.answer(translate(lang, "support.subject_prompt"))
        return
    await state.update_data(subject=subject[:200])
    await state.set_state(SupportStates.message)
    await message.answer(translate(lang, "support.message_prompt"))


@router.message(SupportStates.message)
async def msg_support_message(
    message: Message, state: FSMContext, session, customer: Customer, lang: str
) -> None:
    body = (message.text or message.caption or "").strip()
    if not body:
        await message.answer(translate(lang, "support.message_prompt"))
        return
    data = await state.get_data()
    subject = data.get("subject") or truncate(body, 120)
    try:
        ticket = await ticket_service.create_ticket(
            session, customer, subject, body
        )
    except ConflictError:
        await state.clear()
        await message.answer(translate(lang, "errors.generic"))
        return
    await state.clear()
    await message.answer(
        translate(lang, "support.created", code=escape(ticket.ticket_code)),
        reply_markup=keyboards.support_keyboard(lang, settings.support_username),
    )
    await telegram_notify.notify_admins(
        "<b>Tiket baru</b>\n"
        f"<code>{telegram_notify.escape(ticket.ticket_code)}</code>\n"
        f"Dari: {telegram_notify.escape(customer.display_name)} "
        f"(<code>{customer.telegram_id}</code>)\n"
        f"Subjek: {telegram_notify.escape(subject)}\n\n"
        f"{telegram_notify.escape(truncate(body, 800))}"
    )


@router.callback_query(F.data == "support:list")
async def cb_support_list(callback: CallbackQuery, session, customer: Customer, lang: str) -> None:
    await callback.answer()
    tickets, _ = await ticket_service.list_tickets(
        session, customer_id=customer.id, page_size=10
    )
    if callback.message is None:
        return
    if not tickets:
        await safe_edit(
            callback.message,
            translate(lang, "support.empty"),
            keyboards.back_keyboard(lang, "menu:support"),
        )
        return
    await safe_edit(
        callback.message,
        translate(lang, "support.list_title"),
        keyboards.ticket_list_keyboard(tickets, lang),
    )


@router.callback_query(F.data.startswith("tkt:"))
async def cb_ticket_detail(
    callback: CallbackQuery, session, customer: Customer, lang: str
) -> None:
    try:
        ticket_id = int((callback.data or "").split(":")[1])
        text = await _show_ticket(session, ticket_id, customer, lang)
        ticket = await ticket_service.get_ticket(session, ticket_id)
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "support.not_found"), show_alert=True)
        return
    await callback.answer()
    if callback.message is not None:
        await safe_edit(
            callback.message,
            text,
            keyboards.ticket_thread_keyboard(ticket, lang),
        )


@router.callback_query(F.data.startswith("tktreply:"))
async def cb_ticket_reply(
    callback: CallbackQuery, state: FSMContext, session, customer: Customer, lang: str
) -> None:
    try:
        ticket = await ticket_service.get_ticket(
            session, int((callback.data or "").split(":")[1])
        )
    except (IndexError, ValueError, AppError):
        await callback.answer(translate(lang, "support.not_found"), show_alert=True)
        return
    if ticket.customer_id != customer.id:
        await callback.answer(translate(lang, "support.not_found"), show_alert=True)
        return
    if ticket.status == "CLOSED":
        await callback.answer(translate(lang, "support.closed"), show_alert=True)
        return
    await state.set_state(SupportStates.reply)
    await state.update_data(ticket_id=ticket.id, ticket_code=ticket.ticket_code)
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(
            translate(lang, "support.reply_prompt", code=escape(ticket.ticket_code)),
            reply_markup=keyboards.back_keyboard(lang, f"tkt:{ticket.id}"),
        )


@router.message(SupportStates.reply)
async def msg_ticket_reply(
    message: Message, state: FSMContext, session, customer: Customer, lang: str
) -> None:
    body = (message.text or "").strip()
    data = await state.get_data()
    ticket_id = int(data.get("ticket_id") or 0)
    if not body:
        await message.answer(translate(lang, "support.reply_prompt", code=data.get("ticket_code") or ""))
        return
    try:
        ticket = await ticket_service.get_ticket(session, ticket_id)
        if ticket.customer_id != customer.id:
            raise NotFoundError("Tiket tidak ditemukan")
        await ticket_service.add_message(
            session,
            ticket,
            body,
            sender_type=SenderType.CUSTOMER.value,
            sender_name=customer.display_name,
            sender_telegram_id=customer.telegram_id,
        )
    except (ConflictError, AppError):
        await state.clear()
        await message.answer(translate(lang, "errors.generic"))
        return
    await state.clear()
    await message.answer(translate(lang, "support.replied"))
    await telegram_notify.notify_admins(
        "<b>Balasan tiket</b>\n"
        f"<code>{telegram_notify.escape(ticket.ticket_code)}</code>\n"
        f"Dari: {telegram_notify.escape(customer.display_name)}\n\n"
        f"{telegram_notify.escape(truncate(body, 800))}"
    )
