"""Simple Redis token-bucket rate limiter."""

from __future__ import annotations

import time

import redis.asyncio as redis


class RateLimiter:
    def __init__(self, client: redis.Redis, limit_per_minute: int) -> None:
        self._client = client
        self._limit = limit_per_minute

    async def allow(self, key: str) -> bool:
        bucket = f"kie:rl:{key}:{int(time.time() // 60)}"
        count = await self._client.incr(bucket)
        if count == 1:
            await self._client.expire(bucket, 120)
        return count <= self._limit
