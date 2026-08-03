"""Risk calculation engine with custom org models and explainability."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from gie_contracts.risk import (
    Confidence,
    HeatmapCell,
    ReasoningStep,
    RemediationAction,
    RiskGraphEdge,
    RiskGraphNode,
    RiskInputBundle,
    RiskReport,
    RiskTimelineEvent,
    Severity,
)

from risk_intelligence.domain.scorers import SCORERS, _sev
from risk_intelligence.domain.signals import extract_signals
from risk_intelligence.version import AGENT_VERSION


DEFAULT_WEIGHTS = {s: 1.0 for s in [
    "security", "privacy", "compliance", "identity", "prompt_injection", "jailbreak",
    "hallucination", "supply_chain", "model", "tool_abuse", "data_leakage", "shadow_ai",
    "runtime", "autonomy", "business", "operational",
]}


def _org_weights(org_model: dict[str, Any] | None) -> dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)
    if not org_model:
        return weights
    custom = org_model.get("weights") or org_model.get("category_weights") or {}
    for k, v in custom.items():
        try:
            weights[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return weights


def calculate_risk(bundle: RiskInputBundle, *, prior: RiskReport | None = None) -> RiskReport:
    signals = extract_signals(bundle)
    weights = _org_weights(bundle.org_risk_model)
    steps = [
        ReasoningStep(step=1, action="ingest_inputs", detail="Normalized context, knowledge, compliance, identity, runtime, models, prompts, tools, capabilities", confidence=Confidence(score=1.0)),
        ReasoningStep(step=2, action="extract_signals", detail=f"Derived {len(signals)} signal groups for scoring", confidence=Confidence(score=0.95)),
        ReasoningStep(step=3, action="apply_org_model", detail=f"Using risk model weights from {bundle.org_risk_model.get('model_id') if bundle.org_risk_model else 'default-v1'}", confidence=Confidence(score=1.0)),
    ]
    factors = []
    for scorer in SCORERS:
        factor = scorer(signals, weights)
        if factor is None:
            continue
        factors.append(factor)
        steps.append(
            ReasoningStep(
                step=len(steps) + 1,
                action="score_category",
                detail=f"{factor.category.value}={factor.score:.2f} ({factor.severity.value}): {factor.explanation}",
                category=factor.category.value,
                confidence=factor.confidence,
            )
        )

    category_scores = {f.category.value: f.score for f in factors}
    # Scores already incorporate org weights; overall is mean of category scores.
    overall = max(0.0, min(1.0, sum(f.score for f in factors) / (len(factors) or 1)))
    trust = max(0.0, min(1.0, 1.0 - overall))
    # Boost trust slightly when identity strong and no dangerous tools
    if not signals["weak_identity"] and not signals["dangerous_tools"]:
        trust = min(1.0, trust + 0.05)

    remediations: list[RemediationAction] = []
    seen = set()
    for f in sorted(factors, key=lambda x: x.score, reverse=True):
        for r in f.remediations:
            if r.action_id not in seen:
                remediations.append(r)
                seen.add(r.action_id)

    mappings_summary: dict[str, list[str]] = {"owasp_llm": [], "mitre_atlas": [], "nist_ai_rmf": []}
    for f in factors:
        for m in f.mappings:
            mappings_summary.setdefault(m.framework, [])
            for i in m.ids:
                if i not in mappings_summary[m.framework]:
                    mappings_summary[m.framework].append(i)

    heatmap = []
    for i, f in enumerate(factors):
        heatmap.append(HeatmapCell(category=f.category, score=f.score, severity=f.severity, x=i % 4, y=i // 4))

    nodes = [RiskGraphNode(id="app", kind="Application", label=bundle.agent_id, score=overall)]
    edges = []
    for f in factors:
        nodes.append(RiskGraphNode(id=f.factor_id, kind="RiskFactor", label=f.name, score=f.score, properties={"severity": f.severity.value}))
        edges.append(RiskGraphEdge(source="app", target=f.factor_id, relationship="HAS_RISK"))
        for m in f.mappings:
            mid = f"fw-{m.framework}"
            nodes.append(RiskGraphNode(id=mid, kind="Framework", label=m.framework))
            edges.append(RiskGraphEdge(source=f.factor_id, target=mid, relationship="MAPS_TO"))

    # dedupe nodes
    uniq = {}
    for n in nodes:
        uniq[n.id] = n
    risk_graph = {"nodes": [n.model_dump() for n in uniq.values()], "edges": [e.model_dump() for e in edges]}

    timeline = []
    if prior:
        timeline.extend(prior.timeline[-20:])
        timeline.append(
            RiskTimelineEvent(
                at=datetime.now(timezone.utc),
                event="recalculated",
                overall_score=overall,
                trust_score=trust,
            )
        )
    else:
        timeline.append(
            RiskTimelineEvent(
                at=datetime.now(timezone.utc),
                event="calculated",
                overall_score=overall,
                trust_score=trust,
            )
        )

    digest = hashlib.sha256(json.dumps(bundle.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    overall_conf = sum(f.confidence.score for f in factors) / len(factors) if factors else 0.0
    steps.append(
        ReasoningStep(
            step=len(steps) + 1,
            action="aggregate",
            detail=f"Overall AI risk={overall:.3f}, trust={trust:.3f}, factors={len(factors)}",
            confidence=Confidence(score=overall_conf),
        )
    )

    report = RiskReport(
        tenant_id=bundle.tenant_id,
        agent_id=bundle.agent_id,
        agent_version=AGENT_VERSION,
        factors=factors,
        category_scores=category_scores,
        overall_ai_risk_score=round(overall, 3),
        trust_score=round(trust, 3),
        severity=_sev(overall),
        confidence=Confidence(score=round(overall_conf, 3), rationale="mean factor confidence"),
        reasoning_path=steps,
        remediations=remediations,
        mappings_summary=mappings_summary,
        heatmap=heatmap,
        risk_graph=risk_graph,
        timeline=timeline,
        input_digest=digest,
        model_id=(bundle.org_risk_model or {}).get("model_id", "default-v1") if bundle.org_risk_model else "default-v1",
    )
    if timeline:
        timeline[-1].decision_id = report.report_id
    return report
