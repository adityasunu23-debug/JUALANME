"""Telegram webhook endpoint served by the FastAPI application."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.bot.dispatcher import build_bot, build_dispatcher
from app.core.config import settings

logger = logging.getLogger("app.bot.webhook")

router = APIRouter(prefix="/bot", tags=["bot"])

_lock = asyncio.Lock()
_bot: Bot | None = None
_dispatcher: Dispatcher | None = None


async def _get_runtime() -> tuple[Bot, Dispatcher]:
    global _bot, _dispatcher
    async with _lock:
        if _bot is None:
            _bot = build_bot()
        if _dispatcher is None:
            _dispatcher = build_dispatcher()
    return _bot, _dispatcher


@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request) -> JSONResponse:
    expected = settings.bot_webhook_secret
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="Bot is not configured")

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    bot, dispatcher = await _get_runtime()
    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
    except Exception:
        logger.exception("Failed to process Telegram update")
        raise HTTPException(status_code=500, detail="Update processing failed")
    return JSONResponse({"ok": True})
