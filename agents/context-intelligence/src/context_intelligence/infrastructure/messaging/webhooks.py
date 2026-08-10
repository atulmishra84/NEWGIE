"""Outbound webhook delivery with retries."""

from __future__ import annotations

from typing import Any

import httpx

from context_intelligence.infrastructure.retry import retry_async
from gie_observability.logging import get_logger

logger = get_logger(__name__)


async def deliver_webhook(
    url: str,
    payload: dict[str, Any],
    *,
    secret: str | None = None,
    max_attempts: int = 5,
) -> bool:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "gie-context-intelligence/1.0.0",
    }
    if secret:
        headers["X-GIE-Signature"] = secret

    async def _post() -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

    try:
        await retry_async(_post, max_attempts=max_attempts, retry_on=(httpx.HTTPError,))
        logger.info("webhook_delivered", url=url)
        return True
    except Exception:
        logger.exception("webhook_delivery_failed", url=url)
        return False
