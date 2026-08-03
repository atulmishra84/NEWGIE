"""REST APIs for querying and updating the knowledge graph."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.knowledge import (
    KnowledgeQueryRequest,
    KnowledgeUpsertRequest,
)
from gie_security.auth import AuthPrincipal

from knowledge_intelligence.adapters.rest.deps import container_dep, require_perm
from knowledge_intelligence.application.di import Container
from knowledge_intelligence.domain.rbac import KnowledgePermission
from knowledge_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1", tags=["knowledge"])


def _meta(principal: AuthPrincipal, started: float, confidence: float | None = None, reasoning: list | None = None) -> ResponseMeta:
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


@router.post("/knowledge/query")
async def query_knowledge(
    body: KnowledgeQueryRequest,
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_QUERY)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    result = await container.query_engine.query(
        body,
        tenant_id=principal.tenant_id,
        correlation_id=uuid4().hex,
    )
    return ObservabilityEnvelope(
        data=result,
        meta=_meta(principal, started, result.confidence.score, [s.model_dump() for s in result.reasoning_path]),
    )


@router.post("/knowledge/nodes")
async def upsert_knowledge(
    body: KnowledgeUpsertRequest,
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_WRITE)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    result = await container.upsert.handle(
        body,
        tenant_id=principal.tenant_id,
        actor=principal.subject_id,
        correlation_id=uuid4().hex,
    )
    return ObservabilityEnvelope(data=result, meta=_meta(principal, started))


@router.get("/knowledge/nodes/{node_id}")
async def get_node(
    node_id: str,
    version: str | None = None,
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_READ)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    node = await container.get_node.handle(node_id, version=version)
    return ObservabilityEnvelope(data=node, meta=_meta(principal, started, node.confidence.score))


@router.get("/knowledge/nodes")
async def list_nodes(
    domain: str | None = None,
    kind: str | None = None,
    version: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_READ)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    nodes = await container.nodes.list_nodes(domain=domain, kind=kind, version=version, limit=limit, offset=offset)
    return ObservabilityEnvelope(data={"items": nodes, "count": len(nodes)}, meta=_meta(principal, started))


@router.get("/knowledge/nodes/{node_id}/neighbors")
async def neighbors(
    node_id: str,
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_READ)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    edges = await container.edges.neighbors(node_id)
    return ObservabilityEnvelope(data={"edges": edges}, meta=_meta(principal, started))


@router.post("/knowledge/versions/{version}/publish")
async def publish_version(
    version: str,
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_VERSION)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    nodes = await container.nodes.list_nodes(limit=10000)
    edges = []
    snap = await container.versions.publish(version, checksum="manual", node_count=len(nodes), edge_count=len(edges))
    return ObservabilityEnvelope(data=snap, meta=_meta(principal, started))


@router.get("/knowledge/versions")
async def latest_version(
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_READ)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    snap = await container.versions.latest()
    return ObservabilityEnvelope(data=snap, meta=_meta(principal, started))


@router.get("/knowledge/versions/diff")
async def diff_versions(
    from_version: str = Query(...),
    to_version: str = Query(...),
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_READ)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    diff = await container.diff_versions.handle(from_version, to_version)
    return ObservabilityEnvelope(data=diff, meta=_meta(principal, started))


@router.post("/knowledge/reindex")
async def reindex(
    domain: str | None = None,
    principal: AuthPrincipal = Depends(require_perm(KnowledgePermission.KNOWLEDGE_REINDEX)),
    container: Container = Depends(container_dep),
) -> ObservabilityEnvelope:
    started = time.perf_counter()
    result = await container.reindex.handle(domain=domain)
    return ObservabilityEnvelope(data=result, meta=_meta(principal, started))
