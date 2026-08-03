from __future__ import annotations
import json
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query, Request
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.integration import (
    AuthTokenRequest,
    ConnectRequest,
    IntegrationCatalogResponse,
    PlatformId,
    SyncRequest,
    WebhookIngressRequest,
)
from gie_security.auth import AuthPrincipal
from integration_intelligence.adapters.rest.deps import container_dep, require_perm
from integration_intelligence.application.di import Container
from integration_intelligence.domain.catalog import platform_catalog
from integration_intelligence.domain.engine import circuit_statuses, health_report
from integration_intelligence.domain.rbac import IntegrationPermission
from integration_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1", tags=["integration"])
alias = APIRouter(tags=["integration-alias"])

def _meta(started: float, confidence=None, reasoning=None) -> ResponseMeta:
    return ResponseMeta(
        trace_id=uuid4().hex,
        request_id=uuid4().hex,
        correlation_id=uuid4().hex,
        execution_ms=(time.perf_counter() - started) * 1000,
        confidence=confidence,
        reasoning_path=reasoning or [],
        agent_version=AGENT_VERSION,
        agent_name=AGENT_NAME,
    )

@router.get("/integrations")
@alias.get("/integrations")
async def list_integrations(
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_READ)),
):
    started = time.perf_counter()
    platforms = platform_catalog()
    data = IntegrationCatalogResponse(platforms=platforms, count=len(platforms))
    return ObservabilityEnvelope(data=data, meta=_meta(started, 1.0))

@router.post("/integrations/connect")
@alias.post("/integrations/connect")
async def connect(
    body: ConnectRequest,
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_CONNECT)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    conn = await container.connect.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=conn, meta=_meta(started))

@router.get("/integrations/connections")
@alias.get("/integrations/connections")
async def list_connections(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.connections.list(principal.tenant_id, limit=limit, offset=offset)
    return ObservabilityEnvelope(data={"items": items, "count": len(items)}, meta=_meta(started))


@router.get("/integrations/health/report")
@alias.get("/integrations/health/report")
async def integration_health(
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    conns = await container.connections.list(principal.tenant_id, limit=500)
    hooks = await container.webhooks.list(principal.tenant_id, limit=500)
    audits = await container.audits.list(principal.tenant_id, limit=500)
    report = health_report(principal.tenant_id, conns, hooks, audits)
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score, report.reasoning_path))

@router.get("/integrations/{connection_id}")
@alias.get("/integrations/{connection_id}")
async def get_connection(
    connection_id: UUID,
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    conn = await container.connections.get(connection_id)
    if not conn or conn.tenant_id != principal.tenant_id:
        from integration_intelligence.application.errors import NotFoundError
        raise NotFoundError(f"Connection {connection_id} not found")
    return ObservabilityEnvelope(data=conn, meta=_meta(started))

@router.post("/integrations/{connection_id}/sync")
@alias.post("/integrations/{connection_id}/sync")
async def sync_connection(
    connection_id: UUID,
    body: SyncRequest,
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_SYNC)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    body.connection_id = connection_id
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    result = await container.sync.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=result, meta=_meta(started))

@router.get("/webhooks/deliveries")
@alias.get("/webhooks/deliveries")
async def webhook_deliveries(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.webhooks.list(principal.tenant_id, limit=limit, offset=offset)
    return ObservabilityEnvelope(data={"items": items, "count": len(items)}, meta=_meta(started))

@router.post("/webhooks/{platform_id}")
@alias.post("/webhooks/{platform_id}")
async def webhook_ingress(
    platform_id: PlatformId,
    request: Request,
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_WEBHOOK)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    raw = await request.body()
    try:
        parsed = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        parsed = {}
    if "payload" not in parsed and "event_type" not in parsed:
        body = WebhookIngressRequest(tenant_id=principal.tenant_id, payload=parsed if isinstance(parsed, dict) else {})
    else:
        body = WebhookIngressRequest.model_validate(parsed)
    if request.headers.get("x-hub-signature-256"):
        body.signature = request.headers.get("x-hub-signature-256")
    elif request.headers.get("x-gie-signature"):
        body.signature = request.headers.get("x-gie-signature")
    event = await container.webhook.handle(
        platform_id,
        body,
        raw_body=raw,
        actor=principal.subject_id,
        correlation_id=uuid4().hex,
        tenant_fallback=principal.tenant_id,
    )
    return ObservabilityEnvelope(data=event, meta=_meta(started))

@router.post("/auth/token")
@alias.post("/auth/token")
async def auth_token(
    body: AuthTokenRequest,
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_AUTH)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    token = await container.auth.handle(body, actor=principal.subject_id)
    return ObservabilityEnvelope(data=token, meta=_meta(started))

@router.get("/audit")
@alias.get("/audit")
async def audit_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_AUDIT)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.audits.list(principal.tenant_id, limit=limit, offset=offset)
    return ObservabilityEnvelope(data={"items": items, "count": len(items)}, meta=_meta(started))

@router.get("/health/circuit-breakers")
@alias.get("/health/circuit-breakers")
async def circuit_breakers(
    principal: AuthPrincipal = Depends(require_perm(IntegrationPermission.INTEGRATION_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    conns = await container.connections.list(principal.tenant_id, limit=500)
    items = circuit_statuses(
        conns,
        threshold=container.settings.circuit_failure_threshold,
        open_seconds=container.settings.circuit_open_seconds,
    )
    return ObservabilityEnvelope(data={"items": items, "count": len(items)}, meta=_meta(started))

