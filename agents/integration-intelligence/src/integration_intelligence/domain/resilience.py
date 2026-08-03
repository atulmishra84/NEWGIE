"""Retry + circuit breaker primitives."""

from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, TypeVar
from gie_contracts.integration import ConnectionStatus, IntegrationConnection, utcnow

T = TypeVar("T")

class CircuitOpenError(RuntimeError):
    pass

def _now() -> datetime:
    return datetime.now(timezone.utc)

async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay_ms: int = 100,
) -> tuple[T, int]:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(), attempt - 1
        except Exception as exc:  # noqa: BLE001 — connector boundary
            last_exc = exc
            if attempt >= max_attempts:
                break
            await asyncio.sleep((base_delay_ms / 1000.0) * (2 ** (attempt - 1)))
    assert last_exc is not None
    raise last_exc

def ensure_circuit_allows(conn: IntegrationConnection, *, open_seconds: int) -> None:
    if conn.circuit_breaker_state == "open":
        opened = conn.metadata.get("circuit_opened_at")
        if opened:
            opened_at = datetime.fromisoformat(opened)
            if _now() < opened_at + timedelta(seconds=open_seconds):
                raise CircuitOpenError(f"Circuit open for connection {conn.connection_id}")
            conn.circuit_breaker_state = "half_open"
            conn.status = ConnectionStatus.DEGRADED
        else:
            raise CircuitOpenError(f"Circuit open for connection {conn.connection_id}")

def record_success(conn: IntegrationConnection) -> None:
    conn.failure_count = 0
    conn.circuit_breaker_state = "closed"
    conn.status = ConnectionStatus.CONNECTED
    conn.last_success_at = utcnow()
    conn.last_error = None
    conn.updated_at = utcnow()
    conn.metadata.pop("circuit_opened_at", None)

def record_failure(conn: IntegrationConnection, *, error: str, threshold: int) -> bool:
    """Returns True if circuit just opened."""
    conn.failure_count += 1
    conn.last_error = error
    conn.updated_at = utcnow()
    opened = False
    if conn.failure_count >= threshold:
        conn.circuit_breaker_state = "open"
        conn.status = ConnectionStatus.CIRCUIT_OPEN
        conn.metadata["circuit_opened_at"] = _now().isoformat()
        opened = True
    else:
        conn.status = ConnectionStatus.DEGRADED
    return opened
