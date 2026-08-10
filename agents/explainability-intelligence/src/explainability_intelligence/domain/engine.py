"""Explain decisions across agents with multi-audience views."""

from __future__ import annotations

from typing import Any

from gie_contracts.explainability import (
    AlternativeOption,
    AudienceExplanation,
    AudienceView,
    Confidence,
    ExplainabilityInputBundle,
    ExplanationDimensions,
    ExplanationReport,
    OutputFormat,
    ReasoningPathRequest,
    ReasoningStep,
)

from explainability_intelligence.domain.diagram import (
    build_mermaid,
    figma_diagram_payload,
)
from explainability_intelligence.domain.formats import build_artifacts
from explainability_intelligence.version import AGENT_VERSION

ALL_VIEWS = list(AudienceView)


def _first_rec(bundle: ExplainabilityInputBundle) -> dict[str, Any]:
    if bundle.recommendations:
        return bundle.recommendations[0]
    if bundle.subject:
        return bundle.subject
    return {}


def _evidence(bundle: ExplainabilityInputBundle, rec: dict[str, Any]) -> list[str]:
    evid = list(rec.get("supporting_evidence") or rec.get("evidence") or [])
    for f in (bundle.risk.get("factors") or [])[:5]:
        if isinstance(f, dict):
            evid.append(
                f"Risk {f.get('category')}={f.get('score')} ({f.get('severity')})"
            )
    for g in (bundle.compliance.get("gaps") or [])[:5]:
        if isinstance(g, dict):
            evid.append(
                f"Compliance gap {g.get('control_id') or g.get('title')} ({g.get('severity')})"
            )
    for hit in (bundle.knowledge.get("hits") or [])[:5]:
        if isinstance(hit, dict) and hit.get("node_id"):
            evid.append(f"Knowledge {hit['node_id']}")
    if not evid:
        evid.append("Derived from aggregated GIE agent outputs")
    return [str(e) for e in evid][:15]


def _knowledge_refs(
    bundle: ExplainabilityInputBundle, rec: dict[str, Any]
) -> list[str]:
    refs = list(rec.get("knowledge_refs") or [])
    for hit in (bundle.knowledge.get("hits") or [])[:8]:
        if isinstance(hit, dict) and hit.get("node_id"):
            refs.append(str(hit["node_id"]))
    return sorted(set(refs))[:20]


def _regulation(bundle: ExplainabilityInputBundle, rec: dict[str, Any]) -> str:
    fws = []
    for a in bundle.compliance.get("applicable_frameworks") or []:
        if isinstance(a, dict):
            fws.append(str(a.get("framework") or a.get("id")))
        else:
            fws.append(str(a))
    for ref in rec.get("knowledge_refs") or []:
        fws.append(str(ref))
    fws = [x for x in fws if x]
    if not fws:
        return "No specific regulation triggered; baseline AI governance applies."
    return "Applicable controls/frameworks: " + ", ".join(sorted(set(fws))[:12])


def _policy_source(bundle: ExplainabilityInputBundle, rec: dict[str, Any]) -> str:
    if bundle.policy_package.get("source"):
        return str(bundle.policy_package["source"])
    if bundle.policies.get("source"):
        return str(bundle.policies["source"])
    guards = rec.get("related_guardrails") or []
    if guards:
        return "Policy Generator / Policy Intelligence via " + ", ".join(
            str(g) for g in guards[:6]
        )
    return "GIE policy catalog (derived)"


def _build_dimensions(bundle: ExplainabilityInputBundle) -> ExplanationDimensions:
    rec = _first_rec(bundle)
    title = rec.get("title") or bundle.subject.get("title") or "Decision"
    reason = (
        rec.get("reason")
        or bundle.subject.get("reason")
        or f"Agent decision for {title}"
    )
    biz = (
        rec.get("business_impact")
        or "Reduces operational and regulatory exposure for the AI application."
    )
    risk_txt = (
        f"Priority {rec.get('priority', 'n/a')}; expected risk reduction "
        f"{rec.get('risk_reduction', bundle.risk.get('overall_ai_risk_score', 'n/a'))}."
    )
    if bundle.risk.get("overall_ai_risk_score") is not None:
        risk_txt += f" Overall AI risk score={bundle.risk['overall_ai_risk_score']}."
    conf_score = float(
        (rec.get("confidence") or {}).get("score")
        if isinstance(rec.get("confidence"), dict)
        else rec.get("confidence") or 0.8
    )
    alts = [
        AlternativeOption(
            title="Accept residual risk",
            description="Defer control implementation and monitor.",
            tradeoffs="Lower near-term cost; higher breach/audit exposure.",
            estimated_risk_delta=0.05,
        ),
        AlternativeOption(
            title="Partial control rollout",
            description="Ship highest-priority guardrails only.",
            tradeoffs="Faster delivery; incomplete coverage.",
            estimated_risk_delta=-0.08,
        ),
        AlternativeOption(
            title="Full recommended package",
            description="Implement all related guardrails and policies.",
            tradeoffs="Highest protection; more engineering effort.",
            estimated_risk_delta=-float(rec.get("risk_reduction") or 0.15),
        ),
    ]
    return ExplanationDimensions(
        why=reason,
        evidence=_evidence(bundle, rec),
        risk=risk_txt,
        regulation=_regulation(bundle, rec),
        business_impact=biz,
        confidence=Confidence(
            score=min(0.98, max(0.4, conf_score)),
            rationale="Aggregated from source agent confidence and evidence density",
        ),
        alternative_options=alts,
        expected_outcome=rec.get("expected_outcome")
        or f"Implementing '{title}' should improve trust posture and close related gaps.",
        supporting_knowledge=_knowledge_refs(bundle, rec),
        policy_source=_policy_source(bundle, rec),
    )


def _view(
    audience: AudienceView, dims: ExplanationDimensions, rec: dict[str, Any]
) -> AudienceExplanation:
    title = rec.get("title") or "Decision"
    templates = {
        AudienceView.EXECUTIVE: (
            f"Executive brief: {title}",
            "Business-focused rationale and residual risk tradeoffs.",
            f"We recommend action on '{title}' because {dims.business_impact} "
            f"Confidence {dims.confidence.score:.0%}. Alternatives are available if timeline or budget constrains delivery.",
            ["business_impact", "risk", "expected_outcome", "alternatives"],
        ),
        AudienceView.DEVELOPER: (
            f"Developer guide: {title}",
            "Implementation-oriented explanation with guardrails and dependencies.",
            f"Why: {dims.why} Policy source: {dims.policy_source}. "
            f"Expected outcome: {dims.expected_outcome}. Use supporting knowledge nodes during implementation.",
            ["why", "policy_source", "evidence", "supporting_knowledge"],
        ),
        AudienceView.SECURITY: (
            f"Security analysis: {title}",
            "Threat and control-focused explanation.",
            f"Risk: {dims.risk} Evidence includes {len(dims.evidence)} items. "
            f"Prefer the full package alternative unless compensating controls exist.",
            ["risk", "evidence", "alternatives", "confidence"],
        ),
        AudienceView.COMPLIANCE: (
            f"Compliance narrative: {title}",
            "Regulatory mapping and control obligations.",
            f"Regulation: {dims.regulation} Policy source: {dims.policy_source}. "
            f"This explanation is suitable for control owners and GRC workflows.",
            ["regulation", "policy_source", "evidence", "expected_outcome"],
        ),
        AudienceView.AUDITOR: (
            f"Auditor package: {title}",
            "Traceable decision record with evidence and knowledge lineage.",
            f"Decision '{title}' is justified by documented evidence and knowledge refs. "
            f"Confidence {dims.confidence.score:.0%}. Reproduce via reasoning path and artifacts.",
            [
                "evidence",
                "supporting_knowledge",
                "confidence",
                "policy_source",
                "regulation",
            ],
        ),
    }
    t, s, n, emph = templates[audience]
    # lightly specialize dimensions copy
    view_dims = dims.model_copy(deep=True)
    if audience == AudienceView.EXECUTIVE:
        view_dims.why = f"Strategic: {dims.business_impact}"
    if audience == AudienceView.DEVELOPER:
        view_dims.expected_outcome = (
            f"Ship controls from {dims.policy_source}; validate in CI."
        )
    return AudienceExplanation(
        audience=audience,
        title=t,
        summary=s,
        narrative=n,
        dimensions=view_dims,
        emphasis=emph,
    )


def _normalize_steps(bundle: ExplainabilityInputBundle) -> list[ReasoningStep]:
    steps: list[ReasoningStep] = []
    raw = list(bundle.reasoning_path or [])
    if not raw:
        raw = [
            {
                "step": 1,
                "agent": "context-intelligence",
                "action": "scan",
                "detail": "Normalized application context",
            },
            {
                "step": 2,
                "agent": "risk-intelligence",
                "action": "score",
                "detail": f"Overall risk={bundle.risk.get('overall_ai_risk_score', 'n/a')}",
            },
            {
                "step": 3,
                "agent": "compliance-intelligence",
                "action": "analyze",
                "detail": f"Compliance score={bundle.compliance.get('compliance_score', 'n/a')}",
            },
            {
                "step": 4,
                "agent": "recommendation-intelligence",
                "action": "prioritize",
                "detail": f"{len(bundle.recommendations)} recommendations",
            },
            {
                "step": 5,
                "agent": "policy-generator",
                "action": "generate",
                "detail": "Deployment-ready policies produced",
            },
            {
                "step": 6,
                "agent": "explainability-intelligence",
                "action": "explain",
                "detail": "Multi-audience explanation assembled",
            },
        ]
    for i, item in enumerate(raw, start=1):
        if isinstance(item, ReasoningStep):
            steps.append(item)
            continue
        steps.append(
            ReasoningStep(
                step=int(item.get("step") or i),
                agent=str(item.get("agent") or item.get("producer") or "gie-agent"),
                action=str(item.get("action") or item.get("event_type") or "decide"),
                detail=str(
                    item.get("detail")
                    or item.get("summary")
                    or item.get("title")
                    or "step"
                ),
                inputs=list(item.get("inputs") or []),
                outputs=list(item.get("outputs") or []),
                confidence=Confidence(
                    score=float(
                        (item.get("confidence") or {}).get("score", 0.85)
                        if isinstance(item.get("confidence"), dict)
                        else item.get("confidence") or 0.85
                    )
                ),
            )
        )
    return steps


def explain_decision(bundle: ExplainabilityInputBundle) -> ExplanationReport:
    rec = _first_rec(bundle)
    dims = _build_dimensions(bundle)
    audiences = list(bundle.audiences) if bundle.audiences else list(ALL_VIEWS)
    views = {a.value: _view(a, dims, rec) for a in audiences}
    steps = _normalize_steps(bundle)
    mermaid = build_mermaid(steps, title=str(rec.get("title") or "GIE decision"))
    figma = figma_diagram_payload(
        mermaid,
        name=f"GIE Explanation {bundle.decision_id or bundle.agent_id or 'decision'}",
    )
    summary = (
        f"Explained {bundle.subject_type} decision "
        f"'{rec.get('title') or bundle.decision_id or 'n/a'}' "
        f"across {len(views)} audience views."
    )
    report = ExplanationReport(
        tenant_id=bundle.tenant_id,
        agent_id=bundle.agent_id,
        decision_id=bundle.decision_id or rec.get("recommendation_id"),
        agent_version=AGENT_VERSION,
        subject_type=bundle.subject_type,
        dimensions=dims,
        views=views,
        reasoning_path=steps,
        mermaid_diagram=mermaid,
        figma_diagram=figma,
        confidence=dims.confidence,
        summary=summary,
    )
    formats = (
        list(bundle.formats)
        if bundle.formats
        else [
            OutputFormat.MARKDOWN,
            OutputFormat.HTML,
            OutputFormat.PDF,
            OutputFormat.JSON,
        ]
    )
    report.artifacts = build_artifacts(report, formats)
    return report


def build_reasoning_path(request: ReasoningPathRequest) -> dict[str, Any]:
    bundle = ExplainabilityInputBundle(
        tenant_id=request.tenant_id,
        agent_id=request.agent_id,
        decision_id=request.decision_id,
        reasoning_path=request.steps,
        risk=request.risk,
        compliance=request.compliance,
        recommendations=request.recommendations,
        knowledge=request.knowledge,
    )
    steps = _normalize_steps(bundle)
    mermaid = build_mermaid(steps)
    return {
        "steps": steps,
        "mermaid_diagram": mermaid,
        "figma_diagram": figma_diagram_payload(mermaid, name="GIE Reasoning Path"),
        "step_count": len(steps),
    }
