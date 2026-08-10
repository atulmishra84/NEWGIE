from __future__ import annotations
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.policy import PolicyGenerateRequest
from gie_security.auth import AuthPrincipal
from policy_intelligence.adapters.rest.deps import container_dep, require_perm
from policy_intelligence.application.di import Container
from policy_intelligence.domain.rbac import PolicyPermission
from policy_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1", tags=["policy"])


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


@router.post("/policies/generate")
async def generate_policy(
    body: PolicyGenerateRequest,
    principal: AuthPrincipal = Depends(require_perm(PolicyPermission.POLICY_GENERATE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    # Bind tenant from principal if not set
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    decision = await container.generate.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(
        data=decision,
        meta=_meta(
            started,
            decision.confidence.score,
            [s.model_dump() for s in decision.reasoning_path],
        ),
    )


@router.get("/policies/decisions/{decision_id}")
async def get_decision(
    decision_id: UUID,
    principal: AuthPrincipal = Depends(require_perm(PolicyPermission.POLICY_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    decision = await container.decisions.get(decision_id)
    if not decision:
        from policy_intelligence.application.errors import NotFoundError

        raise NotFoundError(f"Decision not found: {decision_id}")
    return ObservabilityEnvelope(
        data=decision, meta=_meta(started, decision.confidence.score)
    )


@router.get("/policies/decisions")
async def list_decisions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(PolicyPermission.POLICY_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.decisions.list(
        principal.tenant_id, limit=limit, offset=offset
    )
    return ObservabilityEnvelope(
        data={"items": items, "count": len(items)}, meta=_meta(started)
    )


@router.get("/policies/decisions/{decision_id}/explain")
async def explain_decision(
    decision_id: UUID,
    guardrail_id: str | None = None,
    principal: AuthPrincipal = Depends(require_perm(PolicyPermission.POLICY_EXPLAIN)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    data = await container.explain.handle(decision_id, guardrail_id=guardrail_id)
    conf = data.get("confidence")
    score = conf.score if hasattr(conf, "score") else (conf or {}).get("score")
    return ObservabilityEnvelope(data=data, meta=_meta(started, score))


@router.get("/policies/decisions/{decision_id}/artifacts/{filename}")
async def get_artifact(
    decision_id: UUID,
    filename: str,
    principal: AuthPrincipal = Depends(require_perm(PolicyPermission.POLICY_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    decision = await container.decisions.get(decision_id)
    if not decision:
        from policy_intelligence.application.errors import NotFoundError

        raise NotFoundError(f"Decision not found: {decision_id}")
    art = next((a for a in decision.artifacts if a.filename == filename), None)
    if not art:
        from policy_intelligence.application.errors import NotFoundError

        raise NotFoundError(f"Artifact not found: {filename}")
    return ObservabilityEnvelope(data=art, meta=_meta(started))
