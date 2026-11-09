"""Redis cache with transparent in-memory fallback.

The application stays usable when Redis is down (or absent in local dev);
only cache performance degrades.
"""
import json
import time
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings

try:  # pragma: no cover - import guard
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None  # type: ignore[assignment]


class _MemoryCache:
    """Very small TTL cache used when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[float, str]] = {}

    async def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at and expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        expires_at = time.time() + ex if ex else 0
        self._store[key] = (expires_at, value)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._store.pop(key, None)

    async def incr(self, key: str) -> int:
        current = await self.get(key)
        value = int(current or 0) + 1
        await self.set(key, str(value), ex=300)
        return value

    async def close(self) -> None:
        self._store.clear()


class Cache:
    """Facade over Redis with JSON helpers."""

    def __init__(self) -> None:
        self._memory = _MemoryCache()
        self._redis: Optional["Redis"] = None
        self._redis_failed = False

    async def connect(self) -> None:
        if not settings.cache_enabled or Redis is None:
            return
        try:
            client = Redis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
        except Exception:
            self._redis = None
            self._redis_failed = True

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass
        await self._memory.close()

    @property
    def backend(self) -> str:
        return "redis" if self._redis is not None else "memory"

    async def _client(self):
        return self._redis if self._redis is not None else self._memory

    async def get_json(self, key: str) -> Optional[Any]:
        client = await self._client()
        try:
            raw = await client.get(key)
        except Exception:
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = 60) -> None:
        client = await self._client()
        try:
            await client.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception:
            pass

    async def delete(self, *keys: str) -> None:
        client = await self._client()
        try:
            await client.delete(*keys)
        except Exception:
            pass

    async def increment(self, key: str, ttl: int = 300) -> int:
        """Atomic-ish counter used for rate limiting."""
        if self._redis is not None:
            try:
                value = await self._redis.incr(key)
                if value == 1:
                    await self._redis.expire(key, ttl)
                return int(value)
            except Exception:
                pass
        return await self._memory.incr(key)

    async def health(self) -> Dict[str, Any]:
        return {
            "enabled": settings.cache_enabled,
            "backend": self.backend,
            "connected": self._redis is not None,
        }


cache = Cache()