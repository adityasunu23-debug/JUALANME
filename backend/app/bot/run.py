"""Standalone bot entrypoint: python -m app.bot.run"""
from __future__ import annotations

import asyncio
import logging

from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand

from app.bot.dispatcher import build_bot, build_dispatcher
from app.core.config import settings
from app.db.session import session_scope
from app.services import settings_service

logger = logging.getLogger("app.bot")

SETTINGS_SYNC_INTERVAL_SECONDS = 60  # matches settings cache TTL

COMMANDS = [
    BotCommand(command="start", description="Menu utama / Main menu"),
    BotCommand(command="menu", description="Katalog / Catalog"),
    BotCommand(command="orders", description="Pesanan saya / My orders"),
    BotCommand(command="support", description="Bantuan / Support"),
    BotCommand(command="language", description="Bahasa / Language"),
    BotCommand(command="help", description="Bantuan / Help"),
]


async def _sync_runtime_settings() -> None:
    async with session_scope() as session:
        await settings_service.sync_runtime(session)


async def _settings_sync_loop() -> None:
    """Keep bot-process settings in sync with dashboard-managed values."""
    while True:
        try:
            await _sync_runtime_settings()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Runtime settings sync failed")
        await asyncio.sleep(SETTINGS_SYNC_INTERVAL_SECONDS)


async def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        bot = build_bot()
    except RuntimeError as exc:
        logger.error("%s", exc)
        print(
            "\n  BOT_TOKEN belum diisi.\n"
            "  1. Buat bot di @BotFather -> /newbot, salin token.\n"
            "  2. Isi BOT_TOKEN=<token> pada backend/.env\n"
            "  3. Jalankan lagi: python -m app.bot.run\n",
            flush=True,
        )
        return
    dispatcher = build_dispatcher()
    try:
        await _sync_runtime_settings()
        logger.info("Runtime settings synced from database")
        sync_task = asyncio.create_task(
            _settings_sync_loop(), name="bot-settings-sync"
        )
        await bot.set_my_commands(COMMANDS)
        if settings.bot_webhook_url:
            webhook = (
                settings.bot_webhook_url.rstrip("/")
                + "/api/v1/bot/webhook/"
                + settings.bot_webhook_secret
            )
            await bot.set_webhook(webhook, drop_pending_updates=False)
            logger.info("Webhook registered at %s; updates are served by the API", webhook)
            await asyncio.Event().wait()
        else:
            await bot.delete_webhook(drop_pending_updates=False)
            logger.info("Starting Telegram long polling")
            await dispatcher.start_polling(
                bot, allowed_updates=dispatcher.resolve_used_update_types()
            )
    except TelegramUnauthorizedError:
        logger.error("BOT_TOKEN is invalid; the bot cannot authenticate with Telegram")
    finally:
        sync_task.cancel()
        try:
            await sync_task
        except (asyncio.CancelledError, Exception):
            pass
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
