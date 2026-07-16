"""Redis-backed sliding window rate limiting."""

from __future__ import annotations

import time

import redis.asyncio as aioredis

from context_intelligence.domain.ports import RateLimiter


class RedisRateLimiter(RateLimiter):
    """Sliding window counter using a sorted set per tenant/action."""

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

    async def allow(self, tenant_id: str, action: str, limit: int, window_seconds: int) -> bool:
        key = f"ratelimit:{tenant_id}:{action}"
        now = time.time()
        window_start = now - window_seconds
        pipe = self._client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds + 1)
        _, _, count, _ = await pipe.execute()
        return int(count) <= limit
