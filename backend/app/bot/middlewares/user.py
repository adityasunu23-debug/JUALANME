"""Customer context, language resolution and simple flood protection."""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.locales import normalize_language, translate
from app.services import customer_service


def _from_user(event: TelegramObject):
    return getattr(event, "from_user", None)


class UserContextMiddleware(BaseMiddleware):
    """Create/refresh the Customer row and inject it with the language."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = _from_user(event)
        session: AsyncSession | None = data.get("session")
        if user is None or user.is_bot or session is None:
            return await handler(event, data)

        customer = await customer_service.upsert_customer(
            session,
            user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        language = normalize_language(customer.language)
        data["customer"] = customer
        data["lang"] = language

        if customer.is_blocked:
            text = translate(language, "start.blocked")
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(text)
            return None

        return await handler(event, data)


class ThrottleMiddleware(BaseMiddleware):
    """Drop bursts of messages from the same user within a short window."""

    def __init__(self, interval: float = 0.4) -> None:
        self.interval = interval
        self._seen: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = _from_user(event)
        if user is None:
            return await handler(event, data)
        now = time.monotonic()
        last = self._seen.get(user.id, 0.0)
        if now - last < self.interval:
            if isinstance(event, CallbackQuery):
                await event.answer()
            return None
        self._seen[user.id] = now
        if len(self._seen) > 5000:
            cutoff = now - 60
            self._seen = {uid: ts for uid, ts in self._seen.items() if ts >= cutoff}
        return await handler(event, data)
