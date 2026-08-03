"""Category scorers producing explained RiskFactors."""

from __future__ import annotations
from typing import Any, Callable
from gie_contracts.risk import (
    Confidence,
    RemediationAction,
    RiskCategory,
    RiskFactor,
    Severity,
)
from risk_intelligence.domain.mappings import mappings_for

Scorer = Callable[[dict[str, Any], dict[str, float]], RiskFactor | None]

def _sev(score: float) -> Severity:
    if score >= 0.85:
        return Severity.CRITICAL
    if score >= 0.7:
        return Severity.HIGH
    if score >= 0.4:
        return Severity.MEDIUM
    if score >= 0.2:
        return Severity.LOW
    return Severity.INFO

def _factor(category: RiskCategory, name: str, score: float, explanation: str, evidence: list[str], remediations: list[RemediationAction], weight: float = 1.0) -> RiskFactor:
    # Org model weights are applied into score; factor.weight stays in [0,1] for aggregation metadata.
    score = max(0.0, min(1.0, score))
    return RiskFactor(
        factor_id=f"rf-{category.value}",
        category=category,
        name=name,
        score=round(score, 3),
        severity=_sev(score),
        explanation=explanation,
        evidence=evidence,
        confidence=Confidence(score=min(0.95, 0.6 + 0.05 * len(evidence)), rationale="signal-weighted heuristic"),
        mappings=mappings_for(category),
        remediations=remediations,
        weight=max(0.0, min(1.0, float(weight) if weight <= 1.0 else 1.0)),
    )

def _rem(action_id: str, title: str, description: str, guardrails: list[str] | None = None, priority: str = "P1") -> RemediationAction:
    return RemediationAction(
        action_id=action_id,
        title=title,
        description=description,
        priority=priority,
        related_guardrails=guardrails or [],
        knowledge_refs=[],
    )

def score_prompt_injection(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.25
    if sig["has_autonomy"] or sig["frameworks"]:
        base += 0.25
    if sig["has_mcp"] or sig["dangerous_tools"]:
        base += 0.2
    base += min(0.3, float(sig["prompt_risk"]) * 0.5)
    if "langgraph" in sig["frameworks"] or "crewai" in sig["frameworks"]:
        base += 0.1
    w = weights.get(RiskCategory.PROMPT_INJECTION.value, 1.0)
    return _factor(
        RiskCategory.PROMPT_INJECTION,
        "Prompt Injection Risk",
        base * w,
        "AI agent/framework surfaces with tools or untrusted content increase prompt-injection likelihood.",
        [f"frameworks={sig['frameworks']}", f"prompt_risk={sig['prompt_risk']}", f"mcp={sig['has_mcp']}"],
        [_rem("rem-pi-filter", "Deploy prompt-injection input filters", "Add instruction hierarchy and untrusted content isolation.", ["gr-prompt-injection"], "P0")],
        w,
    )

def score_jailbreak(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.2 + (0.4 if sig["jailbreak_markers"] else 0.0) + (0.15 if sig["has_autonomy"] else 0.0)
    w = weights.get(RiskCategory.JAILBREAK.value, 1.0)
    return _factor(
        RiskCategory.JAILBREAK,
        "Jailbreak Risk",
        base * w,
        "Model-facing conversational surfaces can be jailbroken without safety rails.",
        ["jailbreak_markers=" + str(sig["jailbreak_markers"])],
        [_rem("rem-jb", "Enable safety/topic blocklists and output filters", "Apply vendor safety + output scanning.", ["gr-topic-safety", "gr-output-filter"])],
        w,
    )

def score_tool_abuse(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.15 + 0.15 * min(3, len(sig["dangerous_tools"])) + (0.2 if sig["has_mcp"] else 0) + (0.15 if sig["has_autonomy"] else 0)
    w = weights.get(RiskCategory.TOOL_ABUSE.value, 1.0)
    return _factor(
        RiskCategory.TOOL_ABUSE,
        "Tool Abuse Risk",
        base * w,
        "Privileged or dangerous tools without allowlisting enable abuse.",
        [f"dangerous_tools={sig['dangerous_tools']}", f"tools={sig['tool_names'][:8]}"],
        [_rem("rem-tools", "Enforce tool allowlists and human approval", "Deny shell/exec; require approval for high-impact tools.", ["gr-tool-allowlist"], "P0")],
        w,
    )

def score_data_leakage(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.2 + (0.3 if sig["has_pii_context"] else 0) + (0.25 if sig["secrets_detected"] else 0) + (0.1 if sig["public_runtime"] else 0)
    w = weights.get(RiskCategory.DATA_LEAKAGE.value, 1.0)
    return _factor(
        RiskCategory.DATA_LEAKAGE,
        "Data Leakage Risk",
        base * w,
        "PII/PHI/secrets in AI paths or public exposure elevate leakage risk.",
        [f"pii={sig['has_pii_context']}", f"secrets={sig['secrets_detected']}", f"public={sig['public_runtime']}"],
        [_rem("rem-dlp", "Enable DLP/Presidio and output filters", "Scan prompts/completions/logs for sensitive data.", ["gr-pii-presidio", "gr-output-filter"], "P0")],
        w,
    )

def score_privacy(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.2 + (0.35 if sig["has_pii_context"] else 0.1) + (0.1 if "gdpr" in sig["haystack"] or "hipaa" in sig["haystack"] else 0)
    w = weights.get(RiskCategory.PRIVACY.value, 1.0)
    return _factor(RiskCategory.PRIVACY, "Privacy Risk", base * w, "Regulated personal data in AI workflows creates privacy exposure.", [f"pii_context={sig['has_pii_context']}"], [_rem("rem-privacy", "Apply privacy-by-design controls", "Minimize data, anonymize, retain lawfully.", ["gr-pii-presidio"])], w)

def score_compliance(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    fws = sig["compliance_frameworks"]
    base = 0.15 + min(0.5, 0.08 * len(fws if isinstance(fws, list) else [fws])) + (0.2 if sig["has_pii_context"] and not fws else 0.1)
    w = weights.get(RiskCategory.COMPLIANCE.value, 1.0)
    return _factor(RiskCategory.COMPLIANCE, "Compliance Risk", base * w, "Obligations from compliance frameworks require mapped AI controls.", [f"frameworks={fws}"], [_rem("rem-comp", "Map controls to obligations", "Align guardrails to SOC2/GDPR/EU AI Act/HIPAA as applicable.", ["gr-eu-ai-transparency"])], w)

def score_identity(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.45 if sig["weak_identity"] else 0.2
    if sig["has_autonomy"]:
        base += 0.15
    w = weights.get(RiskCategory.IDENTITY.value, 1.0)
    return _factor(RiskCategory.IDENTITY, "Identity Risk", base * w, "Weak or missing strong identity for AI agents increases privilege abuse risk.", [f"weak_identity={sig['weak_identity']}"], [_rem("rem-id", "Enforce workload identity and agent RBAC", "Use OAuth/OIDC, short-lived tokens, least privilege.", ["gr-identity-rbac"], "P1")], w)

def score_security(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.25 + (0.2 if sig["secrets_detected"] else 0) + (0.15 if sig["public_runtime"] else 0) + (0.1 if sig["dangerous_tools"] else 0)
    w = weights.get(RiskCategory.SECURITY.value, 1.0)
    return _factor(RiskCategory.SECURITY, "Security Risk", base * w, "Composite security exposure from secrets, tools, and exposure posture.", ["composite security signals"], [_rem("rem-sec", "Hardening baseline", "Secrets hygiene, network controls, output validation.", ["gr-output-filter", "gr-opa-runtime"])], w)

def score_model(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.2 + min(0.3, 0.08 * sig["model_count"]) + (0.15 if "fine-tune" in sig["haystack"] or "weights" in sig["haystack"] else 0)
    w = weights.get(RiskCategory.MODEL.value, 1.0)
    return _factor(RiskCategory.MODEL, "Model Risk", base * w, "Model inventory size and customization increase model risk.", [f"model_count={sig['model_count']}"], [_rem("rem-model", "Model inventory and access controls", "Track models, restrict extraction, monitor usage.", [])], w)

def score_hallucination(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.35 if sig["frameworks"] or sig["model_count"] else 0.15
    if "rag" not in sig["haystack"] and "grounding" not in sig["haystack"]:
        base += 0.15
    w = weights.get(RiskCategory.HALLUCINATION.value, 1.0)
    return _factor(RiskCategory.HALLUCINATION, "Hallucination Risk", base * w, "Ungrounded generative outputs can be incorrect and over-trusted.", ["grounding_signals_checked"], [_rem("rem-hall", "Add grounding and citation checks", "Require retrieval grounding and human review for high-impact answers.", [])], w)

def score_supply_chain(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.25 + (0.1 * min(3, len(sig["frameworks"]))) + (0.15 if "plugin" in sig["haystack"] or "marketplace" in sig["haystack"] else 0)
    w = weights.get(RiskCategory.SUPPLY_CHAIN.value, 1.0)
    return _factor(RiskCategory.SUPPLY_CHAIN, "Supply Chain Risk", base * w, "Third-party models, plugins, and frameworks expand supply-chain attack surface.", [f"frameworks={sig['frameworks']}"], [_rem("rem-sc", "Vendor and dependency controls", "Pin versions, scan packages, vet model providers.", [])], w)

def score_shadow_ai(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.55 if sig["shadow_ai"] else 0.15
    w = weights.get(RiskCategory.SHADOW_AI.value, 1.0)
    return _factor(RiskCategory.SHADOW_AI, "Shadow AI Risk", base * w, "Unsanctioned AI usage bypasses enterprise controls.", [f"shadow_ai={sig['shadow_ai']}"], [_rem("rem-shadow", "Discover and govern Shadow AI", "CASB/DLP discovery, approved AI catalog, policy enforcement.", [])], w)

def score_runtime(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.2 + (0.25 if sig["public_runtime"] else 0) + (0.15 if "kubernetes" in sig["haystack"] else 0.05)
    w = weights.get(RiskCategory.RUNTIME.value, 1.0)
    return _factor(RiskCategory.RUNTIME, "Runtime Risk", base * w, "Runtime exposure and missing admission controls elevate operational compromise risk.", [f"public_runtime={sig['public_runtime']}"], [_rem("rem-rt", "OPA/runtime restrictions", "Egress allowlists, deny shell, budgets.", ["gr-opa-runtime", "gr-rate-limit"])], w)

def score_autonomy(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.55 if sig["has_autonomy"] else 0.15
    base += 0.1 * min(2, len(sig["dangerous_tools"]))
    w = weights.get(RiskCategory.AUTONOMY.value, 1.0)
    return _factor(RiskCategory.AUTONOMY, "Autonomy Risk", base * w, "Autonomous multi-agent systems can take high-impact actions without oversight.", [f"autonomy={sig['has_autonomy']}"], [_rem("rem-auto", "Human-in-the-loop for high-impact actions", "Cap iterations; require approvals.", ["gr-tool-allowlist"], "P0")], w)

def score_business(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.5 if sig["business_critical"] else 0.25
    base += 0.15 if sig["has_pii_context"] else 0
    w = weights.get(RiskCategory.BUSINESS.value, 1.0)
    return _factor(RiskCategory.BUSINESS, "Business Risk", base * w, "Business criticality amplifies impact of AI failures or breaches.", [f"critical={sig['business_critical']}"], [_rem("rem-biz", "Business impact assessments", "Tier AI systems; apply stricter controls to critical tiers.", [])], w)

def score_operational(sig: dict[str, Any], weights: dict[str, float]) -> RiskFactor:
    base = 0.25 + (0.2 if sig["model_count"] > 2 else 0.05) + (0.15 if sig["has_autonomy"] else 0)
    w = weights.get(RiskCategory.OPERATIONAL.value, 1.0)
    return _factor(RiskCategory.OPERATIONAL, "Operational Risk", base * w, "Operational complexity from models/agents increases failure and cost risk.", [f"models={sig['model_count']}"], [_rem("rem-ops", "SLOs, budgets, and observability", "Rate limits, tracing, cost controls.", ["gr-rate-limit"])], w)

SCORERS: list[Scorer] = [
    score_security,
    score_privacy,
    score_compliance,
    score_identity,
    score_prompt_injection,
    score_jailbreak,
    score_hallucination,
    score_supply_chain,
    score_model,
    score_tool_abuse,
    score_data_leakage,
    score_shadow_ai,
    score_runtime,
    score_autonomy,
    score_business,
    score_operational,
]
