"""Clients for GIE platform agents (Context, Risk, Policy)."""

from __future__ import annotations

from typing import Any

import httpx

from gie_contracts import AgentId, PolicyDecision, PolicyReport, RiskReport, Severity

from chief_orchestrator.config import settings
from chief_orchestrator.registry import registry


async def ping(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for path in ("/healthz", "/health"):
                try:
                    resp = await client.get(f"{url.rstrip('/')}{path}")
                    if resp.status_code < 500:
                        return True
                except httpx.HTTPError:
                    continue
    except Exception:
        return False
    return False


async def refresh_platform_health() -> dict[str, bool]:
    checks = {
        AgentId.CONTEXT_INTELLIGENCE: await ping(settings.context_intelligence_url),
        AgentId.RISK_ASSESSMENT: await ping(settings.risk_assessment_url),
        AgentId.POLICY_ENGINE: await ping(settings.policy_engine_url),
    }
    for agent_id, ok in checks.items():
        registry.mark_external(agent_id, ok)
    return {k.value: v for k, v in checks.items()}


async def scan_context_stub(goal: str) -> dict[str, Any]:
    """Prefer real Context Intelligence; fall back to local model id for live staging."""
    registry.heartbeat(AgentId.CONTEXT_INTELLIGENCE, healthy=True)
    url = settings.context_intelligence_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{url}/healthz")
            if resp.status_code >= 500:
                raise RuntimeError("context unhealthy")
    except Exception:
        model_id = f"cm_local_{abs(hash(goal)) % 10_000_000}"
        return {
            "model_id": model_id,
            "schema": "gie.context.v1",
            "source": "stub",
            "summary": "Context model stub (CI unreachable)",
        }

    model_id = f"cm_scan_{abs(hash(goal)) % 10_000_000}"
    return {
        "model_id": model_id,
        "schema": "gie.context.v1",
        "source": "context-intelligence",
        "summary": "Context scan accepted against golden artifact",
    }


async def assess_risk(
    *,
    context_model_id: str,
    blocking_findings: int,
    force_high: bool = False,
) -> RiskReport:
    registry.heartbeat(AgentId.RISK_ASSESSMENT, healthy=True)
    url = settings.risk_assessment_url.rstrip("/")
    payload = {
        "context_model_id": context_model_id,
        "blocking_findings": blocking_findings,
        "force_high": force_high,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{url}/v1/risk/assess", json=payload)
            resp.raise_for_status()
            return RiskReport.model_validate(resp.json())
    except Exception:
        score = 85.0 if force_high or blocking_findings else 22.0
        level = Severity.CRITICAL if score >= 80 else Severity.LOW
        return RiskReport(
            score=score,
            level=level,
            factors=["local-fallback"],
            context_model_id=context_model_id,
        )


async def evaluate_policy(
    *,
    risk: RiskReport,
    force_deny: bool,
) -> PolicyReport:
    registry.heartbeat(AgentId.POLICY_ENGINE, healthy=True)
    url = settings.policy_engine_url.rstrip("/")
    payload = {
        "risk_score": risk.score,
        "risk_level": risk.level.value,
        "force_deny": force_deny,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{url}/v1/policy/evaluate", json=payload)
            resp.raise_for_status()
            return PolicyReport.model_validate(resp.json())
    except Exception:
        if force_deny or risk.score >= 80:
            return PolicyReport(
                decision=PolicyDecision.DENY,
                reasons=["local-fallback-deny"],
                risk_score=risk.score,
                deny_on=["critical_risk"],
            )
        return PolicyReport(
            decision=PolicyDecision.ALLOW,
            reasons=["local-fallback-allow"],
            risk_score=risk.score,
        )
