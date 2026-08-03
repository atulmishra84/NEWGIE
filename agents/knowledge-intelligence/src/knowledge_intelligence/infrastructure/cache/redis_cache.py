"""Redis cache for query results and rate limits."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from knowledge_intelligence.domain.ports import CacheStore
from knowledge_intelligence.settings import Settings


def create_redis_client(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def ping_redis(client: redis.Redis) -> bool:
    try:
        return bool(await client.ping())
    except Exception:
        return False


class RedisCacheStore(CacheStore):
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self._client.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None:
        await self._client.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)
