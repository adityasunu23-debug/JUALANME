"""Entry points: /start, main menu, help and language selection."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards
from app.bot.common import safe_edit
from app.bot.locales import normalize_language, translate
from app.bot.utils import escape
from app.core.config import settings
from app.models.customer import Customer

router = Router(name="start")


def welcome_text(language: str) -> str:
    return translate(language, "start.welcome", store_name=escape(settings.app_name))


async def show_main_menu(event: Message | CallbackQuery, language: str) -> None:
    markup = keyboards.main_menu(language, settings.support_username)
    if isinstance(event, CallbackQuery) and event.message is not None:
        await safe_edit(event.message, welcome_text(language), markup)
    else:
        message = event if isinstance(event, Message) else event.message
        if message is not None:
            await message.answer(welcome_text(language), reply_markup=markup)


@router.message(CommandStart())
async def cmd_start(message: Message, customer: Customer, lang: str) -> None:
    await message.answer(
        welcome_text(lang), reply_markup=keyboards.main_menu(lang, settings.support_username)
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, lang: str) -> None:
    await message.answer(
        welcome_text(lang), reply_markup=keyboards.main_menu(lang, settings.support_username)
    )


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str) -> None:
    await message.answer(
        translate(lang, "start.help"),
        reply_markup=keyboards.back_keyboard(lang),
    )


@router.message(Command("language"))
async def cmd_language(message: Message, lang: str) -> None:
    await message.answer(translate(lang, "language.title"), reply_markup=keyboards.language_keyboard(lang))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(
        translate(lang, "btn.menu"),
        reply_markup=keyboards.main_menu(lang, settings.support_username),
    )


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
    await show_main_menu(callback, lang)


@router.callback_query(F.data == "menu:language")
async def cb_language_menu(callback: CallbackQuery, lang: str) -> None:
    await callback.answer()
    if callback.message is not None:
        await safe_edit(callback.message, translate(lang, "language.title"), keyboards.language_keyboard(lang))


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(callback: CallbackQuery, customer: Customer, lang: str) -> None:
    chosen = normalize_language((callback.data or "lang:id").split(":", 1)[1])
    customer.language = chosen
    await callback.answer(translate(chosen, "language.changed"))
    await show_main_menu(callback, chosen)


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
