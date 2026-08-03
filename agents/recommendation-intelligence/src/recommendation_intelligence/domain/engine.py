"""Prioritized recommendation generation from risk/compliance/context/knowledge/policies/identity/runtime."""

from __future__ import annotations
import json
from typing import Any
from uuid import uuid4

from gie_contracts.recommendation import (
    Audience,
    AudienceBundle,
    Confidence,
    ImplementationCost,
    ImplementationEffort,
    Priority,
    RecommendationCategory,
    RecommendationInputBundle,
    RecommendationItem,
    RecommendationReport,
    RecommendationStatus,
)

from recommendation_intelligence.version import AGENT_VERSION

# Catalog of recommendation templates keyed by signal
TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "rec-prompt-injection",
        "title": "Deploy prompt-injection defenses",
        "signals": ["prompt_injection", "jailbreak", "llm01"],
        "category": RecommendationCategory.SECURITY,
        "priority_hint": Priority.CRITICAL,
        "reason": "High prompt-injection / jailbreak exposure detected in risk and knowledge signals.",
        "business_impact": "Prevents unauthorized actions, data exfiltration, and brand/regulatory incidents from adversarial prompts.",
        "risk_reduction": 0.22,
        "cost": ImplementationCost.MEDIUM,
        "effort": ImplementationEffort.MEDIUM,
        "time": "1-2 weeks",
        "guardrails": ["gr-prompt-firewall", "gr-input-sanitize"],
        "knowledge": ["owasp-llm01", "atlas-prompt-injection"],
        "audiences": [Audience.SECURITY, Audience.DEVELOPER, Audience.EXECUTIVE],
        "deps": [],
    },
    {
        "id": "rec-pii-presidio",
        "title": "Enforce PII/PHI redaction on outputs",
        "signals": ["privacy", "pii", "phi", "data_leakage", "hipaa", "gdpr"],
        "category": RecommendationCategory.PRIVACY,
        "priority_hint": Priority.CRITICAL,
        "reason": "Privacy/data-leakage risk or healthcare/EU personal data signals present.",
        "business_impact": "Reduces breach likelihood and GDPR/HIPAA exposure; protects customer trust.",
        "risk_reduction": 0.2,
        "cost": ImplementationCost.MEDIUM,
        "effort": ImplementationEffort.LOW,
        "time": "3-5 days",
        "guardrails": ["gr-pii-presidio", "gr-output-filter"],
        "knowledge": ["gdpr-art32", "hipaa-phi"],
        "audiences": [Audience.SECURITY, Audience.DEVELOPER, Audience.EXECUTIVE],
        "deps": [],
    },
    {
        "id": "rec-rbac",
        "title": "Harden agent identity and RBAC",
        "signals": ["identity", "weak_identity", "tool_abuse", "mfa"],
        "category": RecommendationCategory.IDENTITY,
        "priority_hint": Priority.HIGH,
        "reason": "Identity weakness or elevated tool abuse risk requires stronger authZ.",
        "business_impact": "Limits blast radius of compromised agents and insider misuse.",
        "risk_reduction": 0.15,
        "cost": ImplementationCost.MEDIUM,
        "effort": ImplementationEffort.MEDIUM,
        "time": "1 week",
        "guardrails": ["gr-identity-rbac"],
        "knowledge": ["nist-govern", "soc2-cc6"],
        "audiences": [Audience.SECURITY, Audience.PLATFORM, Audience.EXECUTIVE],
        "deps": [],
    },
    {
        "id": "rec-tool-allowlist",
        "title": "Constrain tools with an allowlist + human approval",
        "signals": ["tool_abuse", "shell", "dangerous_tools", "autonomy", "mcp"],
        "category": RecommendationCategory.RUNTIME,
        "priority_hint": Priority.CRITICAL,
        "reason": "Dangerous tools, MCP servers, or high autonomy increase abuse risk.",
        "business_impact": "Stops destructive or data-moving tool calls without approval gates.",
        "risk_reduction": 0.25,
        "cost": ImplementationCost.LOW,
        "effort": ImplementationEffort.MEDIUM,
        "time": "3-7 days",
        "guardrails": ["gr-tool-allowlist", "gr-human-in-loop"],
        "knowledge": ["owasp-llm08", "atlas-tool-abuse"],
        "audiences": [Audience.DEVELOPER, Audience.PLATFORM, Audience.SECURITY],
        "deps": ["rec-rbac"],
    },
    {
        "id": "rec-opa-runtime",
        "title": "Add OPA/runtime policy enforcement",
        "signals": ["runtime", "compliance", "policy", "dora", "soc2"],
        "category": RecommendationCategory.RUNTIME,
        "priority_hint": Priority.HIGH,
        "reason": "Runtime and compliance posture needs enforceable policy-as-code.",
        "business_impact": "Creates auditable deny/allow decisions for regulators and SOC2/DORA controls.",
        "risk_reduction": 0.14,
        "cost": ImplementationCost.MEDIUM,
        "effort": ImplementationEffort.HIGH,
        "time": "2-3 weeks",
        "guardrails": ["gr-opa-runtime"],
        "knowledge": ["soc2-cc7", "dora-ict-risk"],
        "audiences": [Audience.PLATFORM, Audience.SECURITY],
        "deps": ["rec-tool-allowlist"],
    },
    {
        "id": "rec-eu-ai-transparency",
        "title": "Implement EU AI Act transparency notices",
        "signals": ["eu_ai_act", "eu", "transparency", "compliance"],
        "category": RecommendationCategory.COMPLIANCE,
        "priority_hint": Priority.HIGH,
        "reason": "EU AI Act / transparency obligations apply or compliance gaps exist.",
        "business_impact": "Avoids regulatory fines and enables lawful EU market operation.",
        "risk_reduction": 0.1,
        "cost": ImplementationCost.LOW,
        "effort": ImplementationEffort.LOW,
        "time": "2-5 days",
        "guardrails": ["gr-eu-ai-transparency"],
        "knowledge": ["euai-transparency"],
        "audiences": [Audience.EXECUTIVE, Audience.SECURITY, Audience.DEVELOPER],
        "deps": [],
    },
    {
        "id": "rec-rate-limit",
        "title": "Apply rate limits and abuse throttles",
        "signals": ["runtime", "operational", "public", "exposure"],
        "category": RecommendationCategory.OPERATIONS,
        "priority_hint": Priority.MEDIUM,
        "reason": "Public/runtime exposure without throttles increases DoS and cost risk.",
        "business_impact": "Controls spend, availability, and automated abuse.",
        "risk_reduction": 0.08,
        "cost": ImplementationCost.LOW,
        "effort": ImplementationEffort.LOW,
        "time": "1-3 days",
        "guardrails": ["gr-rate-limit"],
        "knowledge": ["soc2-cc7"],
        "audiences": [Audience.PLATFORM, Audience.DEVELOPER],
        "deps": [],
    },
    {
        "id": "rec-supply-chain",
        "title": "Pin and scan AI supply-chain dependencies",
        "signals": ["supply_chain", "model", "shadow_ai"],
        "category": RecommendationCategory.SECURITY,
        "priority_hint": Priority.HIGH,
        "reason": "Model/supply-chain or shadow-AI signals indicate untrusted components.",
        "business_impact": "Reduces poisoned-model and unapproved SaaS AI risk.",
        "risk_reduction": 0.12,
        "cost": ImplementationCost.MEDIUM,
        "effort": ImplementationEffort.MEDIUM,
        "time": "1-2 weeks",
        "guardrails": ["gr-model-allowlist", "gr-sbom"],
        "knowledge": ["owasp-llm05", "atlas-supply-chain"],
        "audiences": [Audience.PLATFORM, Audience.SECURITY, Audience.EXECUTIVE],
        "deps": [],
    },
    {
        "id": "rec-observability",
        "title": "Instrument AI audit logging and tracing",
        "signals": ["operational", "audit", "hipaa-audit", "soc2"],
        "category": RecommendationCategory.OPERATIONS,
        "priority_hint": Priority.MEDIUM,
        "reason": "Audit/ops gaps hinder incident response and compliance evidence.",
        "business_impact": "Speeds investigations and produces auditor-ready evidence trails.",
        "risk_reduction": 0.09,
        "cost": ImplementationCost.MEDIUM,
        "effort": ImplementationEffort.MEDIUM,
        "time": "1 week",
        "guardrails": ["gr-audit-log"],
        "knowledge": ["hipaa-audit", "nist-measure"],
        "audiences": [Audience.PLATFORM, Audience.SECURITY, Audience.EXECUTIVE],
        "deps": [],
    },
    {
        "id": "rec-hallucination",
        "title": "Add groundedness / hallucination controls",
        "signals": ["hallucination", "rag", "business"],
        "category": RecommendationCategory.SECURITY,
        "priority_hint": Priority.MEDIUM,
        "reason": "Hallucination or business-critical answers need grounding checks.",
        "business_impact": "Reduces incorrect decisions and liability from fabricated outputs.",
        "risk_reduction": 0.11,
        "cost": ImplementationCost.HIGH,
        "effort": ImplementationEffort.HIGH,
        "time": "2-4 weeks",
        "guardrails": ["gr-groundedness", "gr-citation-required"],
        "knowledge": ["owasp-llm06"],
        "audiences": [Audience.DEVELOPER, Audience.SECURITY],
        "deps": [],
    },
    {
        "id": "rec-compliance-gaps",
        "title": "Close critical compliance control gaps",
        "signals": ["gap", "missing", "critical", "compliance_score"],
        "category": RecommendationCategory.COMPLIANCE,
        "priority_hint": Priority.CRITICAL,
        "reason": "Compliance analysis shows critical/high gaps against applicable frameworks.",
        "business_impact": "Avoids audit failure, fines, and blocked product launches in regulated markets.",
        "risk_reduction": 0.18,
        "cost": ImplementationCost.HIGH,
        "effort": ImplementationEffort.HIGH,
        "time": "3-6 weeks",
        "guardrails": ["gr-opa-runtime", "gr-output-filter"],
        "knowledge": ["iso27001", "soc2"],
        "audiences": [Audience.EXECUTIVE, Audience.SECURITY],
        "deps": ["rec-opa-runtime", "rec-pii-presidio"],
    },
    {
        "id": "rec-secret-hygiene",
        "title": "Rotate exposed secrets and block secret egress",
        "signals": ["secret", "api_key", "security"],
        "category": RecommendationCategory.SECURITY,
        "priority_hint": Priority.CRITICAL,
        "reason": "Context scan found secrets or high security risk around credentials.",
        "business_impact": "Prevents account takeover and cloud spend abuse.",
        "risk_reduction": 0.2,
        "cost": ImplementationCost.LOW,
        "effort": ImplementationEffort.LOW,
        "time": "1-2 days",
        "guardrails": ["gr-secret-scanner", "gr-output-filter"],
        "knowledge": ["owasp-llm02"],
        "audiences": [Audience.DEVELOPER, Audience.PLATFORM, Audience.SECURITY],
        "deps": [],
    },
]


def _haystack(bundle: RecommendationInputBundle) -> str:
    return json.dumps(
        {
            "risk": bundle.risk,
            "compliance": bundle.compliance,
            "context": bundle.context,
            "knowledge": bundle.knowledge,
            "policies": bundle.policies,
            "identity": bundle.identity,
            "runtime": bundle.runtime,
        },
        default=str,
    ).lower()


def _extract_evidence(bundle: RecommendationInputBundle, signals: list[str]) -> list[str]:
    evidence: list[str] = []
    hay = _haystack(bundle)
    for s in signals:
        if s in hay:
            evidence.append(f"Signal matched: {s}")
    # Structured pulls
    risk = bundle.risk or {}
    if isinstance(risk.get("overall_ai_risk_score"), (int, float)):
        evidence.append(f"Overall AI risk score={risk['overall_ai_risk_score']}")
    for f in (risk.get("factors") or [])[:8]:
        if isinstance(f, dict) and f.get("category") and f.get("score") is not None:
            if any(sig in str(f.get("category", "")).lower() for sig in signals) or float(f.get("score", 0)) >= 0.6:
                evidence.append(f"Risk factor {f.get('category')}={f.get('score')} ({f.get('severity', 'n/a')})")
    for rem in (risk.get("remediations") or [])[:5]:
        if isinstance(rem, dict) and rem.get("title"):
            evidence.append(f"Risk remediation: {rem['title']}")
    comp = bundle.compliance or {}
    if comp.get("compliance_score") is not None:
        evidence.append(f"Compliance score={comp.get('compliance_score')}")
    for g in (comp.get("gaps") or [])[:6]:
        if isinstance(g, dict):
            evidence.append(f"Compliance gap: {g.get('control_id') or g.get('title')} ({g.get('severity')})")
    for hit in (bundle.knowledge.get("hits") or [])[:5]:
        if isinstance(hit, dict) and hit.get("node_id"):
            evidence.append(f"Knowledge: {hit['node_id']}")
    ctx = bundle.context or {}
    secrets = ((ctx.get("data") or {}).get("secret_findings") or [])
    if secrets:
        evidence.append(f"Context secret findings count={len(secrets)}")
    tools = ((ctx.get("interfaces") or {}).get("tools") or [])
    if tools:
        evidence.append(f"Context tools count={len(tools)}")
    if not evidence:
        evidence.append("Derived from aggregated GIE input bundle")
    return evidence[:12]


def _priority_score(priority: Priority, risk_reduction: float, effort: ImplementationEffort, confidence: float) -> float:
    p_w = {Priority.CRITICAL: 40, Priority.HIGH: 30, Priority.MEDIUM: 18, Priority.LOW: 8}[priority]
    e_w = {ImplementationEffort.LOW: 12, ImplementationEffort.MEDIUM: 8, ImplementationEffort.HIGH: 4}[effort]
    return round(min(100.0, p_w + risk_reduction * 100 * 0.35 + e_w + confidence * 10), 2)


def _adjust_priority(hint: Priority, evidence: list[str], hay: str) -> Priority:
    critical_markers = ("critical", "secret", "phi", "prompt_injection", "shell", "gap")
    if hint == Priority.CRITICAL:
        return Priority.CRITICAL
    if any(m in " ".join(evidence).lower() or m in hay for m in critical_markers) and hint in {Priority.HIGH, Priority.MEDIUM}:
        # bump one level
        order = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        return order[min(order.index(hint) + 1, 3)]
    if "low" in hay and hint == Priority.HIGH and "critical" not in hay:
        return Priority.MEDIUM
    return hint


def generate_recommendations(bundle: RecommendationInputBundle) -> RecommendationReport:
    hay = _haystack(bundle)
    reasoning: list[dict[str, Any]] = [
        {"step": 1, "action": "ingest_inputs", "detail": "Normalized risk, compliance, context, knowledge, policies, identity, runtime"},
        {"step": 2, "action": "match_templates", "detail": f"Evaluating {len(TEMPLATES)} recommendation templates"},
    ]
    items: list[RecommendationItem] = []
    for tmpl in TEMPLATES:
        matched = [s for s in tmpl["signals"] if s in hay]
        # Always include baseline ops if runtime present and nothing else matched for rate-limit
        if not matched and tmpl["id"] not in {"rec-rate-limit", "rec-observability"}:
            continue
        if not matched and tmpl["id"] in {"rec-rate-limit", "rec-observability"}:
            if "runtime" not in hay and "operational" not in hay and "exposure" not in hay:
                continue
            matched = ["baseline-ops"]
        evidence = _extract_evidence(bundle, tmpl["signals"])
        conf = min(0.98, 0.55 + 0.08 * len(matched) + (0.1 if evidence else 0))
        priority = _adjust_priority(tmpl["priority_hint"], evidence, hay)
        # Soften if overall risk very low
        overall = bundle.risk.get("overall_ai_risk_score")
        if isinstance(overall, (int, float)) and overall < 0.25 and priority == Priority.CRITICAL:
            priority = Priority.HIGH
        item = RecommendationItem(
            recommendation_id=f"{tmpl['id']}-{uuid4().hex[:6]}",
            title=tmpl["title"],
            reason=tmpl["reason"] + (f" Matched: {', '.join(matched[:5])}." if matched else ""),
            business_impact=tmpl["business_impact"],
            risk_reduction=tmpl["risk_reduction"],
            implementation_cost=tmpl["cost"],
            implementation_effort=tmpl["effort"],
            estimated_time=tmpl["time"],
            priority=priority,
            confidence=Confidence(score=round(conf, 3), rationale="signal + evidence match"),
            supporting_evidence=evidence,
            dependencies=list(tmpl.get("deps") or []),
            category=tmpl["category"],
            audiences=list(tmpl["audiences"]),
            related_guardrails=list(tmpl.get("guardrails") or []),
            knowledge_refs=list(tmpl.get("knowledge") or []),
            status=RecommendationStatus.PROPOSED,
            priority_score=_priority_score(priority, tmpl["risk_reduction"], tmpl["effort"], conf),
        )
        items.append(item)
        reasoning.append(
            {
                "step": len(reasoning) + 1,
                "action": "emit_recommendation",
                "detail": f"{item.title} -> {item.priority.value} (score={item.priority_score})",
                "category": item.category.value,
            }
        )

    items.sort(key=lambda r: (-r.priority_score, r.title))
    by_priority: dict[str, list[RecommendationItem]] = {p.value: [] for p in Priority}
    for it in items:
        by_priority[it.priority.value].append(it)

    def for_audience(aud: Audience) -> list[RecommendationItem]:
        return [i for i in items if aud in i.audiences]

    exec_items = for_audience(Audience.EXECUTIVE)
    dev_items = for_audience(Audience.DEVELOPER)
    sec_items = for_audience(Audience.SECURITY)
    plat_items = for_audience(Audience.PLATFORM)

    by_audience = {
        Audience.EXECUTIVE.value: AudienceBundle(
            audience=Audience.EXECUTIVE,
            summary=f"{len(exec_items)} executive-facing recommendations emphasizing business impact and regulatory risk.",
            items=exec_items,
        ),
        Audience.DEVELOPER.value: AudienceBundle(
            audience=Audience.DEVELOPER,
            summary=f"{len(dev_items)} developer actions for prompts, tools, and application guardrails.",
            items=dev_items,
        ),
        Audience.SECURITY.value: AudienceBundle(
            audience=Audience.SECURITY,
            summary=f"{len(sec_items)} security-team controls spanning threat, privacy, and compliance.",
            items=sec_items,
        ),
        Audience.PLATFORM.value: AudienceBundle(
            audience=Audience.PLATFORM,
            summary=f"{len(plat_items)} platform/runtime and supply-chain hardening items.",
            items=plat_items,
        ),
    }

    counts = {
        "total": len(items),
        "critical": len(by_priority["critical"]),
        "high": len(by_priority["high"]),
        "medium": len(by_priority["medium"]),
        "low": len(by_priority["low"]),
    }
    summary = (
        f"{counts['total']} recommendations "
        f"(critical={counts['critical']}, high={counts['high']}, medium={counts['medium']}, low={counts['low']})"
    )
    avg_conf = sum(i.confidence.score for i in items) / len(items) if items else 0.0
    return RecommendationReport(
        tenant_id=bundle.tenant_id,
        agent_id=bundle.agent_id,
        agent_version=AGENT_VERSION,
        recommendations=items,
        by_priority=by_priority,
        by_audience=by_audience,
        executive_recommendations=exec_items,
        developer_recommendations=dev_items,
        security_team_recommendations=sec_items,
        platform_team_recommendations=plat_items,
        confidence=Confidence(score=round(avg_conf, 3), rationale="aggregate template confidence"),
        reasoning_path=reasoning,
        summary=summary,
        counts=counts,
    )


def approve_recommendations(
    report: RecommendationReport,
    *,
    recommendation_ids: list[str],
    approve_all: bool = False,
) -> RecommendationReport:
    wanted = set(recommendation_ids)
    updated: list[RecommendationItem] = []
    for item in report.recommendations:
        data = item.model_copy(deep=True)
        if approve_all or data.recommendation_id in wanted:
            data.status = RecommendationStatus.APPROVED
        updated.append(data)
    report.recommendations = updated
    # rebuild audience slices with updated status
    report.executive_recommendations = [i for i in updated if Audience.EXECUTIVE in i.audiences]
    report.developer_recommendations = [i for i in updated if Audience.DEVELOPER in i.audiences]
    report.security_team_recommendations = [i for i in updated if Audience.SECURITY in i.audiences]
    report.platform_team_recommendations = [i for i in updated if Audience.PLATFORM in i.audiences]
    report.by_priority = {p.value: [i for i in updated if i.priority == p] for p in Priority}
    report.summary = report.summary + f"; approved={sum(1 for i in updated if i.status == RecommendationStatus.APPROVED)}"
    return report
