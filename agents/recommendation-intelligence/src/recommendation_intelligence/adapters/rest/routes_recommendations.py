from __future__ import annotations
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, Query
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.recommendation import RecommendationApproveRequest, RecommendationGenerateRequest
from gie_security.auth import AuthPrincipal
from recommendation_intelligence.adapters.rest.deps import container_dep, require_perm
from recommendation_intelligence.application.di import Container
from recommendation_intelligence.application.errors import NotFoundError
from recommendation_intelligence.domain.rbac import RecommendationPermission
from recommendation_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1/recommendations", tags=["recommendations"])
alias = APIRouter(prefix="/recommendations", tags=["recommendations-alias"])

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

@router.post("")
@router.post("/")
@alias.post("")
@alias.post("/")
async def generate(
    body: RecommendationGenerateRequest,
    principal: AuthPrincipal = Depends(require_perm(RecommendationPermission.REC_GENERATE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    report = await container.generate.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score, report.reasoning_path))

@router.get("/history")
@alias.get("/history")
async def history(
    agent_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(RecommendationPermission.REC_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.reports.history(principal.tenant_id, agent_id=agent_id, limit=limit, offset=offset)
    return ObservabilityEnvelope(data={"items": items, "count": len(items)}, meta=_meta(started))

@router.post("/approve")
@alias.post("/approve")
async def approve(
    body: RecommendationApproveRequest,
    principal: AuthPrincipal = Depends(require_perm(RecommendationPermission.REC_APPROVE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    report = await container.approve.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score, report.reasoning_path))

@router.get("/{agent_id}")
@alias.get("/{agent_id}")
async def get_for_agent(
    agent_id: str,
    principal: AuthPrincipal = Depends(require_perm(RecommendationPermission.REC_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    report = await container.reports.latest_for_agent(principal.tenant_id, agent_id)
    if not report:
        raise NotFoundError(f"No recommendations for agent {agent_id}")
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score, report.reasoning_path))
