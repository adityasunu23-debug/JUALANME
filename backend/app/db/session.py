"""Async database engine and session management."""
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_db_path = settings.database_url.split("///")[-1] if settings.is_sqlite else ""
if _db_path and _db_path not in (":memory:", ""):
    directory = os.path.dirname(os.path.abspath(_db_path))
    if directory:
        os.makedirs(directory, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    future=True,
    pool_pre_ping=True,
)

if settings.is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()


SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Context manager used by the bot, workers and background tasks."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database() -> bool:
    """Health check helper."""
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return True


async def dispose_engine() -> None:
    await engine.dispose()
