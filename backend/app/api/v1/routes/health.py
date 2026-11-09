"""Service health endpoint."""
import logging

from fastapi import APIRouter

from app.core.cache import cache
from app.core.config import settings
from app.db.session import check_database
from app.schemas.stats import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    database_ok = True
    try:
        await check_database()
    except Exception:
        logger.exception("Database health check failed")
        database_ok = False
    cache_info = await cache.health()
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        app=settings.app_name,
        version=VERSION,
        environment=settings.app_env,
        database=database_ok,
        cache=str(cache_info.get("backend", "memory")),
        payment_provider=settings.payment_provider,
        bot_configured=bool(settings.bot_token),
    )
