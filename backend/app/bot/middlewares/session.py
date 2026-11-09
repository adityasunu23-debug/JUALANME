"""Per-update database session middleware."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Open one AsyncSession per Telegram update and commit at the end."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with SessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                logger.exception("Bot handler failed, database session rolled back")
                raise
            else:
                try:
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
            return result
