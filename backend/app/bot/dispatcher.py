"""Bot and dispatcher factories."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import build_router
from app.bot.middlewares import DbSessionMiddleware, ThrottleMiddleware, UserContextMiddleware
from app.core.config import settings


def build_bot() -> Bot:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.message.middleware(DbSessionMiddleware())
    dispatcher.callback_query.middleware(DbSessionMiddleware())
    dispatcher.message.middleware(UserContextMiddleware())
    dispatcher.callback_query.middleware(UserContextMiddleware())
    dispatcher.message.middleware(ThrottleMiddleware())
    dispatcher.callback_query.middleware(ThrottleMiddleware())
    dispatcher.include_router(build_router())
    return dispatcher
