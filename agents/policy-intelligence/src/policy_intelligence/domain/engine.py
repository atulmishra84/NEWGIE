"""Core policy determination engine."""

from __future__ import annotations

import json
from typing import Any

from gie_contracts.policy import (
    Confidence,
    GuardrailRecommendation,
    PolicyInputBundle,
    Priority,
    ReasoningStep,
)

from policy_intelligence.domain.catalog import CATALOG, GuardrailSpec


def _flatten_signals(bundle: PolicyInputBundle) -> str:
    parts = [
        json.dumps(bundle.context, default=str),
        json.dumps(bundle.risk, default=str),
        json.dumps(bundle.compliance, default=str),
        json.dumps(bundle.knowledge, default=str),
        json.dumps(bundle.identity, default=str),
        json.dumps(bundle.business, default=str),
    ]
    return " ".join(parts).lower()


def _matched_triggers(spec: GuardrailSpec, haystack: str) -> list[str]:
    return [t for t in spec.triggers if t in haystack]


def _boost_priority(priority: Priority, business: dict[str, Any]) -> Priority:
    criticality = str(business.get("criticality", business.get("tier", ""))).lower()
    if criticality in {"critical", "tier0", "systemic"} and priority != Priority.P0:
        order = [Priority.P0, Priority.P1, Priority.P2, Priority.P3]
        idx = order.index(priority)
        return order[max(0, idx - 1)]
    return priority


def determine_guardrails(
    bundle: PolicyInputBundle,
) -> tuple[list[GuardrailRecommendation], list[ReasoningStep], Confidence]:
    haystack = _flatten_signals(bundle)
    steps: list[ReasoningStep] = [
        ReasoningStep(
            step=1,
            action="ingest_inputs",
            detail="Normalized context/risk/compliance/knowledge/identity/business metadata",
            confidence=Confidence(score=1.0),
        ),
        ReasoningStep(
            step=2,
            action="scan_catalog",
            detail=f"Evaluating {len(CATALOG)} guardrail templates against input signals",
            confidence=Confidence(score=1.0),
        ),
    ]
    recs: list[GuardrailRecommendation] = []
    for spec in CATALOG:
        matched = _matched_triggers(spec, haystack)
        if not matched and not _force_baseline(spec, bundle):
            continue
        if not matched:
            matched = ["baseline_secure_default"]
        conf = min(0.98, 0.55 + 0.08 * len(matched))
        if (
            bundle.risk.get("overall_score", 0)
            and float(bundle.risk.get("overall_score", 0)) >= 0.7
        ):
            conf = min(0.99, conf + 0.1)
        priority = _boost_priority(spec.priority, bundle.business)
        why = [spec.why_template.format(signals=", ".join(matched[:6]))]
        if bundle.compliance:
            frameworks = (
                bundle.compliance.get("frameworks")
                or bundle.compliance.get("controls")
                or []
            )
            if frameworks:
                why.append(
                    f"Compliance context references: "
                    f"{frameworks if isinstance(frameworks, str) else ', '.join(str(x) for x in list(frameworks)[:8])}"
                )
        if bundle.identity:
            why.append(
                "Identity metadata indicates authenticated AI workload requiring policy binding."
            )
        recs.append(
            GuardrailRecommendation(
                guardrail_id=spec.guardrail_id,
                name=spec.name,
                category=spec.category,
                applies=True,
                why=why,
                priority=priority,
                confidence=Confidence(
                    score=round(conf, 3), rationale=f"matched triggers: {matched[:5]}"
                ),
                business_impact=spec.business_impact,
                implementation_effort=spec.effort,
                knowledge_refs=list(spec.knowledge_ids),
                risk_refs=_risk_refs(bundle, matched),
                compliance_refs=_compliance_refs(bundle),
                controls=list(spec.controls),
            )
        )
        steps.append(
            ReasoningStep(
                step=len(steps) + 1,
                action="apply_guardrail",
                detail=f"Selected {spec.guardrail_id} ({priority.value}) — {spec.name}",
                inputs=matched[:8],
                confidence=Confidence(score=conf),
            )
        )

    # Priority sort
    order = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2, Priority.P3: 3}
    recs.sort(key=lambda r: (order[r.priority], -r.confidence.score))
    overall = sum(r.confidence.score for r in recs) / len(recs) if recs else 0.0
    steps.append(
        ReasoningStep(
            step=len(steps) + 1,
            action="rank_and_score",
            detail=f"Produced {len(recs)} applicable guardrails; overall confidence {overall:.2f}",
            confidence=Confidence(score=overall),
        )
    )
    return (
        recs,
        steps,
        Confidence(score=round(overall, 3), rationale="mean recommendation confidence"),
    )


def _force_baseline(spec: GuardrailSpec, bundle: PolicyInputBundle) -> bool:
    # Always recommend core rails when any AI framework present
    frameworks = json.dumps(
        bundle.context.get("ai", bundle.context), default=str
    ).lower()
    has_ai = any(
        x in frameworks
        for x in ("openai", "langgraph", "crewai", "autogen", "foundry", "llm", "agent")
    )
    return has_ai and spec.guardrail_id in {
        "gr-prompt-injection",
        "gr-output-filter",
        "gr-tool-allowlist",
    }


def _risk_refs(bundle: PolicyInputBundle, matched: list[str]) -> list[str]:
    refs = []
    for item in (
        bundle.risk.get("findings", [])
        if isinstance(bundle.risk.get("findings"), list)
        else []
    ):
        if isinstance(item, dict) and item.get("id"):
            refs.append(str(item["id"]))
    if not refs and matched:
        refs = [f"signal:{m}" for m in matched[:3]]
    return refs[:10]


def _compliance_refs(bundle: PolicyInputBundle) -> list[str]:
    refs = []
    for key in ("frameworks", "controls", "obligations"):
        val = bundle.compliance.get(key)
        if isinstance(val, list):
            refs.extend(str(x) for x in val[:5])
        elif isinstance(val, str):
            refs.append(val)
    return refs[:10]
