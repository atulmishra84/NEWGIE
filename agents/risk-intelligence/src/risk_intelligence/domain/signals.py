"""Extract risk signals from input bundle."""

from __future__ import annotations
import json
from typing import Any
from gie_contracts.risk import RiskInputBundle


def as_text(*parts: Any) -> str:
    return " ".join(
        json.dumps(p, default=str) if not isinstance(p, str) else p for p in parts
    ).lower()


def extract_signals(bundle: RiskInputBundle) -> dict[str, Any]:
    ctx = bundle.context_model or {}
    ai = ctx.get("ai", ctx)
    interfaces = ctx.get("interfaces", {})
    tools = bundle.tool_permissions or interfaces.get("tools") or []
    tool_names = []
    for t in tools if isinstance(tools, list) else tools.get("allowed", []):
        tool_names.append(t.get("name", str(t)) if isinstance(t, dict) else str(t))
    dangerous = [
        n
        for n in tool_names
        if any(
            x in n.lower() for x in ("shell", "exec", "python", "sql", "file", "email")
        )
    ]
    frameworks = []
    for f in ai.get("frameworks", []) if isinstance(ai, dict) else []:
        frameworks.append(f.get("name", str(f)) if isinstance(f, dict) else str(f))
    models = (
        bundle.ai_models or (ai.get("models") if isinstance(ai, dict) else []) or []
    )
    prompts = bundle.prompt_analysis or {}
    identity = bundle.identity_metadata or ctx.get("security", {})
    runtime = bundle.runtime_configuration or ctx.get("deployment", {})
    compliance = bundle.compliance_requirements or {}
    caps = bundle.agent_capabilities or ai.get("autonomous_capabilities") or []
    hay = as_text(
        ctx,
        bundle.knowledge_graph,
        compliance,
        identity,
        runtime,
        prompts,
        caps,
        models,
        tools,
    )
    return {
        "haystack": hay,
        "frameworks": [str(f).lower() for f in frameworks],
        "tool_names": tool_names,
        "dangerous_tools": dangerous,
        "model_count": len(models) if isinstance(models, list) else 0,
        "has_mcp": "mcp" in hay or bool(interfaces.get("mcp_servers")),
        "has_autonomy": any(
            x in hay
            for x in (
                "autonomous",
                "agency",
                "multi-agent",
                "crewai",
                "autogen",
                "langgraph",
            )
        ),
        "has_pii_context": any(
            x in hay
            for x in ("pii", "phi", "hipaa", "gdpr", "personal data", "healthcare")
        ),
        "weak_identity": not any(
            x in as_text(identity)
            for x in ("oauth", "oidc", "entra", "workload", "mfa")
        ),
        "public_runtime": any(
            x in as_text(runtime) for x in ("public", "internet", "0.0.0.0", "no auth")
        ),
        "prompt_risk": float(
            prompts.get("injection_likelihood", prompts.get("risk_score", 0) or 0)
        ),
        "jailbreak_markers": any(
            x in hay for x in ("jailbreak", "dan", "bypass safety")
        ),
        "shadow_ai": any(
            x in hay
            for x in ("shadow", "unsanctioned", "personal chatgpt", "unapproved")
        ),
        "compliance_frameworks": compliance.get("frameworks")
        or compliance.get("controls")
        or [],
        "business_critical": str(
            (bundle.context_model or {}).get("business", {}).get("criticality", "")
        ).lower()
        in {"critical", "tier0"},
        "secrets_detected": "secret" in hay
        or "api_key" in hay
        or bool((ctx.get("data") or {}).get("secret_findings")),
    }
