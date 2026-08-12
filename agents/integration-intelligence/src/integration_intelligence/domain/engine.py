"""Core integration connect / sync / webhook / health logic."""

from __future__ import annotations
from gie_contracts.integration import (
    AuditLogEntry,
    CircuitBreakerStatus,
    Confidence,
    ConnectRequest,
    ConnectionStatus,
    DeliveryStatus,
    IntegrationConnection,
    IntegrationHealthReport,
    SyncRequest,
    SyncResult,
    WebhookEvent,
    WebhookIngressRequest,
)
from integration_intelligence.domain.auth_tokens import verify_webhook_signature
from integration_intelligence.domain.catalog import get_platform, platform_catalog
from integration_intelligence.domain.connectors import (
    ConnectorError,
    simulate_inbound_sync,
    simulate_outbound_sync,
    validate_connect,
)
from integration_intelligence.domain.resilience import (
    CircuitOpenError,
    ensure_circuit_allows,
    record_failure,
    record_success,
    with_retry,
)
from integration_intelligence.version import AGENT_VERSION


def build_connection(
    request: ConnectRequest, *, warnings: list[str]
) -> IntegrationConnection:
    platform = get_platform(request.platform_id)
    assert platform
    status = ConnectionStatus.CONNECTED if not warnings else ConnectionStatus.DEGRADED
    if request.dry_run:
        status = ConnectionStatus.PENDING
    return IntegrationConnection(
        tenant_id=request.tenant_id,
        platform_id=request.platform_id,
        name=request.name,
        status=status,
        auth_method=request.auth_method,
        config={
            k: v
            for k, v in (request.config or {}).items()
            if "secret" not in k.lower() and "password" not in k.lower()
        },
        scopes=request.scopes,
        endpoint_url=request.endpoint_url,
        metadata={
            "warnings": warnings,
            "capabilities": platform.capabilities,
            "dry_run": request.dry_run,
        },
    )


async def run_sync(
    conn: IntegrationConnection,
    request: SyncRequest,
    *,
    failure_threshold: int,
    open_seconds: int,
    max_attempts: int,
    base_delay_ms: int,
) -> SyncResult:
    ensure_circuit_allows(conn, open_seconds=open_seconds)
    import time

    started = time.perf_counter()
    retries = 0
    try:

        async def _do():
            if request.direction == "inbound":
                return await simulate_inbound_sync(conn.platform_id, request.payload)
            if request.direction == "bidirectional":
                out_s, _, _ = await simulate_outbound_sync(
                    conn.platform_id, request.payload
                )
                _, in_r, msg = await simulate_inbound_sync(
                    conn.platform_id, request.payload
                )
                return out_s, in_r, msg
            return await simulate_outbound_sync(conn.platform_id, request.payload)

        # force failure for tests / chaos
        if request.payload.get("_force_fail") and not request.force:

            async def _fail():
                raise RuntimeError("Forced connector failure")

            result, retries = await with_retry(
                _fail, max_attempts=max_attempts, base_delay_ms=base_delay_ms
            )
        else:
            result, retries = await with_retry(
                _do, max_attempts=max_attempts, base_delay_ms=base_delay_ms
            )
        sent, received, message = result
        record_success(conn)
        return SyncResult(
            connection_id=conn.connection_id,
            tenant_id=conn.tenant_id,
            platform_id=conn.platform_id,
            status="success",
            records_sent=sent,
            records_received=received,
            retries=retries,
            duration_ms=int((time.perf_counter() - started) * 1000),
            message=message,
        )
    except CircuitOpenError as exc:
        return SyncResult(
            connection_id=conn.connection_id,
            tenant_id=conn.tenant_id,
            platform_id=conn.platform_id,
            status="circuit_open",
            retries=retries,
            duration_ms=int((time.perf_counter() - started) * 1000),
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        opened = record_failure(conn, error=str(exc), threshold=failure_threshold)
        return SyncResult(
            connection_id=conn.connection_id,
            tenant_id=conn.tenant_id,
            platform_id=conn.platform_id,
            status="failed" if not opened else "circuit_open",
            retries=retries,
            duration_ms=int((time.perf_counter() - started) * 1000),
            message=str(exc),
        )


def ingest_webhook(
    platform_id,
    body: WebhookIngressRequest,
    *,
    raw_body: bytes,
    hmac_secret: str,
    tenant_fallback: str,
) -> WebhookEvent:
    tenant = body.tenant_id or tenant_fallback
    sig_ok = None
    if body.signature is not None:
        sig_ok = verify_webhook_signature(raw_body, body.signature, hmac_secret)
    status = DeliveryStatus.DELIVERED if sig_ok is not False else DeliveryStatus.FAILED
    return WebhookEvent(
        tenant_id=tenant,
        platform_id=platform_id,
        event_type=body.event_type,
        payload=body.payload,
        signature_valid=sig_ok,
        delivery_status=status,
        attempts=1,
        last_error=None if sig_ok is not False else "Invalid webhook signature",
    )


def health_report(
    tenant_id: str,
    connections: list[IntegrationConnection],
    webhooks: list[WebhookEvent],
    audits: list[AuditLogEntry],
) -> IntegrationHealthReport:
    connected = sum(1 for c in connections if c.status == ConnectionStatus.CONNECTED)
    degraded = sum(1 for c in connections if c.status == ConnectionStatus.DEGRADED)
    circuit_open = sum(
        1 for c in connections if c.status == ConnectionStatus.CIRCUIT_OPEN
    )
    score = 0.9
    if circuit_open:
        score -= 0.2 * min(circuit_open, 3)
    if degraded:
        score -= 0.05 * min(degraded, 4)
    score = max(0.2, min(0.99, score))
    return IntegrationHealthReport(
        tenant_id=tenant_id,
        connections_total=len(connections),
        connected=connected,
        degraded=degraded,
        circuit_open=circuit_open,
        webhook_deliveries_24h=len(webhooks),
        audit_events_24h=len(audits),
        confidence=Confidence(
            score=round(score, 3), rationale="Derived from connection + circuit health"
        ),
        reasoning_path=[
            {
                "step": "catalog",
                "detail": f"{len(platform_catalog())} platforms supported",
            },
            {"step": "connections", "detail": f"{len(connections)} registered"},
            {"step": "circuits", "detail": f"{circuit_open} open"},
        ],
        summary=f"{connected}/{len(connections)} connected; {circuit_open} circuit(s) open",
    )


def circuit_statuses(
    connections: list[IntegrationConnection], *, threshold: int, open_seconds: int
) -> list[CircuitBreakerStatus]:
    out: list[CircuitBreakerStatus] = []
    for c in connections:
        opened_at = None
        next_attempt = None
        raw = c.metadata.get("circuit_opened_at")
        if raw:
            from datetime import datetime, timedelta

            opened_at = datetime.fromisoformat(raw)
            next_attempt = opened_at + timedelta(seconds=open_seconds)
        out.append(
            CircuitBreakerStatus(
                connection_id=c.connection_id,
                platform_id=c.platform_id,
                state=c.circuit_breaker_state,
                failure_count=c.failure_count,
                failure_threshold=threshold,
                opened_at=opened_at,
                next_attempt_at=next_attempt,
            )
        )
    return out


__all__ = [
    "ConnectorError",
    "build_connection",
    "run_sync",
    "ingest_webhook",
    "health_report",
    "circuit_statuses",
    "validate_connect",
    "AGENT_VERSION",
]
