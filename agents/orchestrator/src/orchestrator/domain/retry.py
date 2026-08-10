"""Retry strategies for agent invocation."""

from __future__ import annotations
import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class RetryableError(RuntimeError):
    pass


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int,
    base_delay_ms: int,
    retryable: Callable[[Exception], bool] | None = None,
) -> tuple[T, int]:
    """Exponential backoff retry. Returns (result, retries_used)."""
    last: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(), attempt - 1
        except Exception as exc:  # noqa: BLE001
            last = exc
            can = (
                retryable(exc)
                if retryable
                else isinstance(exc, RetryableError)
                or "timeout" in str(exc).lower()
                or "unavailable" in str(exc).lower()
            )
            if attempt >= max_attempts or not can:
                break
            await asyncio.sleep((base_delay_ms / 1000.0) * (2 ** (attempt - 1)))
    assert last is not None
    raise last
