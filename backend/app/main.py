"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

import app.models  # noqa: F401 - ensure every table is registered
from app.api.v1.api_router import api_router
from app.core.cache import cache
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import dispose_engine, engine, session_scope
from app.models.admin import Admin
from app.models.enums import AdminRole
from app.services import settings_service
from app.workers.scheduler import start_workers, stop_workers

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("app")

VERSION = "1.0.0"


async def _seed_owner_admins() -> None:
    async with session_scope() as session:
        for telegram_id in settings.admin_telegram_id_list:
            existing = await session.execute(
                select(Admin).where(Admin.telegram_id == telegram_id)
            )
            if existing.scalar_one_or_none() is None:
                session.add(
                    Admin(
                        telegram_id=telegram_id,
                        role=AdminRole.OWNER.value,
                        is_active=True,
                        notes="Seeded from ADMIN_TELEGRAM_IDS",
                    )
                )
        await session.flush()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await cache.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_scope() as session:
        created = await settings_service.seed_defaults(session)
        await settings_service.sync_runtime(session)
        if created:
            logger.info("Seeded %s default settings", created)
    await _seed_owner_admins()
    tasks = start_workers()
    try:
        yield
    finally:
        await stop_workers()
        await cache.close()
        await dispose_engine()
        if tasks:
            logger.info("Background workers stopped")


app = FastAPI(
    title=settings.app_name,
    version=VERSION,
    description="Telegram Store API - catalogue, crypto payments and delivery.",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")

if settings.bot_token and settings.bot_webhook_secret:
    from app.bot.webhook import router as bot_webhook_router

    app.include_router(bot_webhook_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "app": settings.app_name,
        "version": VERSION,
        "docs": "/docs" if not settings.is_production else None,
        "health": "/api/v1/health",
    }


def run() -> None:  # pragma: no cover - manual entrypoint
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=not settings.is_production)


if __name__ == "__main__":  # pragma: no cover
    run()
