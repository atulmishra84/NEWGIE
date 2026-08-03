from __future__ import annotations
import time
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query
from gie_contracts.envelope import ObservabilityEnvelope, ResponseMeta
from gie_contracts.explainability import ExplainRequest, ReasoningPathRequest
from gie_security.auth import AuthPrincipal
from explainability_intelligence.adapters.rest.deps import container_dep, require_perm
from explainability_intelligence.application.di import Container
from explainability_intelligence.application.errors import NotFoundError
from explainability_intelligence.domain.diagram import figma_diagram_payload
from explainability_intelligence.domain.rbac import ExplainPermission
from explainability_intelligence.version import AGENT_NAME, AGENT_VERSION

router = APIRouter(prefix="/v1", tags=["explainability"])
alias = APIRouter(tags=["explainability-alias"])

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

@router.post("/explain")
@alias.post("/explain")
async def explain(
    body: ExplainRequest,
    principal: AuthPrincipal = Depends(require_perm(ExplainPermission.EXPLAIN_GENERATE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.bundle.tenant_id:
        body.bundle.tenant_id = principal.tenant_id
    report = await container.explain.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(
        data=report,
        meta=_meta(started, report.confidence.score, [s.model_dump() for s in report.reasoning_path]),
    )

@router.get("/explanation/{explanation_id}")
@alias.get("/explanation/{explanation_id}")
async def get_explanation(
    explanation_id: UUID,
    principal: AuthPrincipal = Depends(require_perm(ExplainPermission.EXPLAIN_READ)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    report = await container.explanations.get(explanation_id)
    if not report:
        raise NotFoundError(f"Explanation {explanation_id} not found")
    return ObservabilityEnvelope(data=report, meta=_meta(started, report.confidence.score))

@router.post("/reasoning/path")
@alias.post("/reasoning/path")
async def reasoning_path(
    body: ReasoningPathRequest,
    principal: AuthPrincipal = Depends(require_perm(ExplainPermission.EXPLAIN_GENERATE)),
    container: Container = Depends(container_dep),
):
    started = time.perf_counter()
    if not body.tenant_id:
        body.tenant_id = principal.tenant_id
    result = await container.reasoning.handle(body, actor=principal.subject_id, correlation_id=uuid4().hex)
    return ObservabilityEnvelope(data=result, meta=_meta(started))

@router.get("/figma-generate-diagram")
@alias.get("/figma-generate-diagram")
async def figma_generate_diagram(
    explanation_id: UUID | None = Query(default=None),
    principal: AuthPrincipal = Depends(require_perm(ExplainPermission.EXPLAIN_READ)),
    container: Container = Depends(container_dep),
):
    """Return FigJam-ready generate_diagram payload (Mermaid flowchart)."""
    started = time.perf_counter()
    if explanation_id:
        report = await container.explanations.get(explanation_id)
        if not report:
            raise NotFoundError(f"Explanation {explanation_id} not found")
        payload = report.figma_diagram or figma_diagram_payload(report.mermaid_diagram)
        payload["explanation_id"] = str(report.explanation_id)
        payload["mermaidSyntax"] = report.mermaid_diagram
    else:
        # baseline template diagram for GIE explainability pipeline
        mermaid = """flowchart LR
  startNode(["Agent decision"])
  riskNode["Risk Intelligence"]
  compNode["Compliance Intelligence"]
  recNode["Recommendation Intelligence"]
  polNode["Policy Generator"]
  expNode["Explainability"]
  outNode([Audience artifacts])
  startNode --> riskNode
  startNode --> compNode
  riskNode --> recNode
  compNode --> recNode
  recNode --> polNode
  polNode --> expNode
  expNode ==> outNode"""
        payload = figma_diagram_payload(mermaid, name="GIE Explainability Pipeline")
    return ObservabilityEnvelope(data=payload, meta=_meta(started))
