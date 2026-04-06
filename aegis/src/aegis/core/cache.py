"""Redis cache wrapper for Aegis."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from aegis.core.config import get_config

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis_url: str | None = None) -> None:
        config = get_config()
        self._url = redis_url or config.redis.url
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def get(self, key: str) -> Any | None:
        try:
            value = await self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception:
            logger.warning("Cache get failed for key: %s", key)
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                await self.client.setex(key, ttl, serialized)
            else:
                await self.client.set(key, serialized)
            return True
        except Exception:
            logger.warning("Cache set failed for key: %s", key)
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True
        except Exception:
            logger.warning("Cache delete failed for key: %s", key)
            return False

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self.client.exists(key))
        except Exception:
            return False

    async def increment(self, key: str, ttl: int | None = None) -> int:
        try:
            count = await self.client.incr(key)
            if ttl and count == 1:
                await self.client.expire(key, ttl)
            return count
        except Exception:
            logger.warning("Cache increment failed for key: %s", key)
            return 0

    async def ping(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False


_cache_instance: RedisCache | None = None


def get_cache() -> RedisCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
