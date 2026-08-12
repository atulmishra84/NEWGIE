"""Scan REST routes."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.sources import ScanSource
from pydantic import BaseModel

from context_intelligence.adapters.rest.deps import (
    AuthContext,
    get_event_publisher,
    get_idempotency_cache,
    get_outbox,
    get_rate_limiter,
    get_repository,
    require_read,
    require_write,
)
from context_intelligence.domain.ports import (
    ContextRepository,
    EventPublisher,
    IdempotencyCache,
    OutboxWriter,
    RateLimiter,
)
from context_intelligence.domain.scan_executor import request_scan
from context_intelligence.infrastructure.celery_app import execute_scan_task
from context_intelligence.settings import get_settings
from context_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1/scans", tags=["scans"])


class CreateScanRequest(BaseModel):
    source: ScanSource
    idempotency_key: str | None = None
    webhook_url: str | None = None


def _meta(request: Request) -> ResponseMeta:
    ctx = getattr(request.state, "obs_context", None)
    return ResponseMeta(
        trace_id=ctx.trace_id if ctx else "",
        request_id=ctx.request_id if ctx else "",
        correlation_id=ctx.correlation_id if ctx else "",
        execution_ms=getattr(request.state, "execution_ms", 0.0),
        agent_version=AGENT_VERSION,
        agent_name=AGENT_NAME,
        reasoning_path=ctx.reasoning_path if ctx else [],
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    request: Request,
    body: CreateScanRequest,
    auth: Annotated[AuthContext, Depends(require_write)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
    outbox: Annotated[OutboxWriter, Depends(get_outbox)],
    publisher: Annotated[EventPublisher, Depends(get_event_publisher)],
    idempotency: Annotated[IdempotencyCache, Depends(get_idempotency_cache)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    idempotency_key_header: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
) -> ObservabilityEnvelope[dict[str, Any]]:
    settings = get_settings()
    key = body.idempotency_key or idempotency_key_header or str(uuid4())
    if not await rate_limiter.allow(
        auth.tenant_id,
        "scan_create",
        settings.rate_limit_requests,
        settings.rate_limit_window_seconds,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    cached = await idempotency.get(auth.tenant_id, key)
    if cached:
        existing = await repo.get_scan(UUID(cached), auth.tenant_id)
        if existing:
            return ObservabilityEnvelope(data=existing, meta=_meta(request))

    ctx = getattr(request.state, "obs_context", None)
    correlation_id = ctx.correlation_id if ctx else uuid4().hex
    record = await request_scan(
        repo,
        outbox,
        publisher,
        tenant_id=auth.tenant_id,
        source=body.source,
        requested_by=auth.subject,
        idempotency_key=key,
        correlation_id=correlation_id,
        webhook_url=body.webhook_url,
    )
    await idempotency.set(auth.tenant_id, key, record["scan_id"])
    execute_scan_task.delay(record["scan_id"], auth.tenant_id, correlation_id)
    await repo.write_audit_log(
        tenant_id=auth.tenant_id,
        actor=auth.subject,
        action="scan.create",
        resource_type="scan",
        resource_id=record["scan_id"],
    )
    return ObservabilityEnvelope(data=record, meta=_meta(request))


@router.get("/{scan_id}")
async def get_scan(
    request: Request,
    scan_id: UUID,
    auth: Annotated[AuthContext, Depends(require_read)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
) -> ObservabilityEnvelope[dict[str, Any]]:
    record = await repo.get_scan(scan_id, auth.tenant_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
        )
    return ObservabilityEnvelope(data=record, meta=_meta(request))


@router.get("")
async def list_scans(
    request: Request,
    auth: Annotated[AuthContext, Depends(require_read)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
) -> ObservabilityEnvelope[dict[str, Any]]:
    items = await repo.list_scans(
        auth.tenant_id, limit=limit, offset=offset, status=status_filter
    )
    return ObservabilityEnvelope(
        data={"items": items, "limit": limit, "offset": offset}, meta=_meta(request)
    )


@router.post("/{scan_id}/cancel")
async def cancel_scan(
    request: Request,
    scan_id: UUID,
    auth: Annotated[AuthContext, Depends(require_write)],
    repo: Annotated[ContextRepository, Depends(get_repository)],
) -> ObservabilityEnvelope[dict[str, Any]]:
    record = await repo.get_scan(scan_id, auth.tenant_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
        )
    if record["status"] in {"completed", "failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scan already {record['status']}",
        )
    await repo.update_scan_status(scan_id, status="cancelled")
    updated = await repo.get_scan(scan_id, auth.tenant_id)
    await repo.write_audit_log(
        tenant_id=auth.tenant_id,
        actor=auth.subject,
        action="scan.cancel",
        resource_type="scan",
        resource_id=str(scan_id),
    )
    return ObservabilityEnvelope(data=updated or {}, meta=_meta(request))
