"""Redis cache for idempotency, models, and rate limits."""

from __future__ import annotations

from uuid import UUID

import redis.asyncio as aioredis

from context_intelligence.domain.ports import IdempotencyCache, ModelCache
from context_intelligence.settings import Settings, get_settings


class RedisIdempotencyCache(IdempotencyCache):
    def __init__(self, client: aioredis.Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds

    def _key(self, tenant_id: str, key: str) -> str:
        return f"idempotency:{tenant_id}:{key}"

    async def get(self, tenant_id: str, key: str) -> str | None:
        value = await self._client.get(self._key(tenant_id, key))
        return value.decode() if value else None

    async def set(self, tenant_id: str, key: str, scan_id: str) -> None:
        await self._client.set(self._key(tenant_id, key), scan_id, ex=self._ttl)


class RedisModelCache(ModelCache):
    def __init__(self, client: aioredis.Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds

    def _key(self, tenant_id: str, model_id: UUID, version: int | None) -> str:
        ver = version if version is not None else "latest"
        return f"model:{tenant_id}:{model_id}:{ver}"

    async def get(
        self, tenant_id: str, model_id: UUID, version: int | None
    ) -> str | None:
        value = await self._client.get(self._key(tenant_id, model_id, version))
        return value.decode() if value else None

    async def set(
        self, tenant_id: str, model_id: UUID, version: int | None, payload: str
    ) -> None:
        await self._client.set(
            self._key(tenant_id, model_id, version), payload, ex=self._ttl
        )


def create_redis_client(settings: Settings | None = None) -> aioredis.Redis:
    cfg = settings or get_settings()
    return aioredis.from_url(cfg.redis_url, decode_responses=False)


async def ping_redis(client: aioredis.Redis) -> bool:
    try:
        return bool(await client.ping())
    except Exception:
        return False
