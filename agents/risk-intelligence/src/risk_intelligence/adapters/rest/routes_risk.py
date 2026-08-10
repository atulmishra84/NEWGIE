from __future__ import annotations
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, Query
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.risk import RiskCalculateRequest, RiskRecalculateRequest
from gie_security.auth import AuthPrincipal
from risk_intelligence.adapters.rest.deps import container_dep, require_perm
from risk_intelligence.application.di import Container
from risk_intelligence.application.errors import NotFoundError
from risk_intelligence.domain.rbac import RiskPermission
from risk_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1/risk", tags=["risk"])
# Also expose unversioned aliases matching the product API contract
alias = APIRouter(prefix="/risk", tags=["risk-alias"])


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


async def _calculate(
    body: RiskCalculateRequest, principal: AuthPrincipal, container: Container
):
    started = time.perf_counter()
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    report = await container.calculate.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(
        data=report,
        meta=_meta(
            started,
            report.confidence.score,
            [s.model_dump() for s in report.reasoning_path],
        ),
    )


async def _recalculate(
    body: RiskRecalculateRequest, principal: AuthPrincipal, container: Container
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    report = await container.recalculate.handle(
        body, actor=principal.subject_id, correlation_id=uuid4().hex
    )
    return ObservabilityEnvelope(
        data=report,
        meta=_meta(
            started,
            report.confidence.score,
            [s.model_dump() for s in report.reasoning_path],
        ),
    )


@router.post("/calculate")
@alias.post("/calculate")
async def calculate_risk(
    body: RiskCalculateRequest,
    principal: AuthPrincipal = Depends(require_perm(RiskPermission.RISK_CALCULATE)),
    container: Container = Depends(container_dep),
):
    return await _calculate(body, principal, container)


@router.post("/recalculate")
@alias.post("/recalculate")
async def recalculate_risk(
    body: RiskRecalculateRequest,
    principal: AuthPrincipal = Depends(require_perm(RiskPermission.RISK_CALCULATE)),
    container: Container = Depends(container_dep),
):
    return await _recalculate(body, principal, container)


@router.get("/history")
@alias.get("/history")
async def risk_history(
    agent_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(require_perm(RiskPermission.RISK_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    items = await container.reports.history(
        principal.tenant_id, agent_id=agent_id, limit=limit, offset=offset
    )
    return ObservabilityEnvelope(
        data={
            "items": items,
            "count": len(items),
            "timeline": [e for r in items for e in r.timeline],
        },
        meta=_meta(started),
    )


@router.get("/remediation")
@alias.get("/remediation")
async def risk_remediation(
    agent_id: str = Query(...),
    principal: AuthPrincipal = Depends(require_perm(RiskPermission.RISK_REMEDIATE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    report = await container.reports.latest_for_agent(principal.tenant_id, agent_id)
    if not report:
        raise NotFoundError(f"No risk report for agent {agent_id}")
    return ObservabilityEnvelope(
        data={
            "agent_id": agent_id,
            "report_id": str(report.report_id),
            "overall_ai_risk_score": report.overall_ai_risk_score,
            "remediations": report.remediations,
            "by_category": {f.category.value: f.remediations for f in report.factors},
        },
        meta=_meta(started, report.confidence.score),
    )


@router.get("/dashboard/{agent_id}")
async def risk_dashboard(
    agent_id: str,
    principal: AuthPrincipal = Depends(require_perm(RiskPermission.RISK_READ)),
    container: Container = Depends(container_dep),
):
    """Risk Dashboard API — report + heatmap + graph + timeline."""
    started = time.perf_counter()
    report = await container.reports.latest_for_agent(principal.tenant_id, agent_id)
    if not report:
        raise NotFoundError(f"No risk report for agent {agent_id}")
    return ObservabilityEnvelope(
        data={
            "report": report,
            "heatmap": report.heatmap,
            "risk_graph": report.risk_graph,
            "timeline": report.timeline,
            "category_scores": report.category_scores,
            "overall_ai_risk_score": report.overall_ai_risk_score,
            "trust_score": report.trust_score,
        },
        meta=_meta(started, report.confidence.score),
    )


@router.get("/{agent_id}")
@alias.get("/{agent_id}")
async def get_risk_for_agent(
    agent_id: str,
    principal: AuthPrincipal = Depends(require_perm(RiskPermission.RISK_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    report = await container.reports.latest_for_agent(principal.tenant_id, agent_id)
    if not report:
        raise NotFoundError(f"No risk report for agent {agent_id}")
    return ObservabilityEnvelope(
        data=report,
        meta=_meta(
            started,
            report.confidence.score,
            [s.model_dump() for s in report.reasoning_path],
        ),
    )
