"""Exponential backoff with jitter."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


def compute_backoff(
    attempt: int,
    *,
    base_seconds: float = 0.5,
    max_seconds: float = 30.0,
    jitter: float = 0.25,
) -> float:
    delay = min(max_seconds, base_seconds * (2**attempt))
    return delay + random.uniform(0, delay * jitter)


def retry_sync(
    fn: Callable[[], T],
    *,
    max_attempts: int = 5,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except retry_on as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                break
            time.sleep(compute_backoff(attempt))
    assert last_exc is not None
    raise last_exc


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 5,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except retry_on as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                break
            await asyncio.sleep(compute_backoff(attempt))
    assert last_exc is not None
    raise last_exc
