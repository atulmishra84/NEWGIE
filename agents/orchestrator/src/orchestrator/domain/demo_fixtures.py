"""Rich demo agent payloads for sandbox / E2E testing."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


def is_demo_request(payload: dict[str, Any]) -> bool:
    """Treat known demo tenants / paths as fixture scenarios."""
    tenant = str(payload.get("tenant_id") or "").lower()
    source = payload.get("source") or {}
    path = str(source.get("path") or payload.get("path") or "").lower()
    meta = payload.get("metadata") or {}
    options = payload.get("options") or {}
    if meta.get("demo") is True or options.get("demo") is True:
        return True
    if tenant in {"acme", "azure-demo", "demo", "gie-demo"}:
        return True
    markers = ("/demo", "demo-ai", "acme-ai", "demo-app", "sample-ai")
    return any(m in path for m in markers)


def demo_payload(agent_id: str, version: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return a realistic per-agent analysis slice for dashboard E2E demos."""
    tenant = payload.get("tenant_id") or "demo"
    source = payload.get("source") or {}
    path = source.get("path") or "/demo/acme-ai-assistant"
    art = uuid4().hex[:10]

    catalog: dict[str, dict[str, Any]] = {
        "context": {
            "summary": "Discovered ACME AI Assistant: FastAPI + RAG chat service with Azure OpenAI.",
            "assets": [
                {"id": "svc-chat", "type": "service", "name": "chat-api", "runtime": "python3.12"},
                {"id": "model-gpt", "type": "model", "name": "gpt-4o-mini", "provider": "azure-openai"},
                {"id": "store-vec", "type": "vector_store", "name": "acme-docs-qdrant"},
            ],
            "data_flows": [
                {"from": "user", "to": "chat-api", "data": "prompt"},
                {"from": "chat-api", "to": "azure-openai", "data": "prompt+context"},
                {"from": "chat-api", "to": "postgres", "data": "chat_history"},
            ],
            "confidence": 0.91,
        },
        "knowledge": {
            "summary": "Mapped frameworks: NIST AI RMF, ISO 42001, SOC2; 14 control themes applicable.",
            "frameworks": ["NIST-AI-RMF", "ISO-42001", "SOC2-CC6"],
            "evidence": [
                {"id": "ev-1", "title": "Model card missing for gpt-4o-mini", "severity": "high"},
                {"id": "ev-2", "title": "Prompt logging retains PII 90 days", "severity": "medium"},
            ],
            "confidence": 0.88,
        },
        "risk": {
            "summary": "Overall risk score 72/100 (elevated). Top risks: prompt injection, PII retention, model drift.",
            "score": 72,
            "findings": [
                {"id": "r1", "title": "Unvalidated user prompts reach LLM", "severity": "high", "likelihood": 0.8},
                {"id": "r2", "title": "Chat history stores emails without redaction", "severity": "high", "likelihood": 0.7},
                {"id": "r3", "title": "No offline eval gate before model swap", "severity": "medium", "likelihood": 0.6},
            ],
            "confidence": 0.86,
        },
        "compliance": {
            "summary": "6 gaps vs NIST AI RMF Govern/Map; SOC2 logging retention exceeds policy.",
            "gaps": [
                {"control": "GOVERN-1.2", "status": "gap", "note": "No AI accountability owner documented"},
                {"control": "MAP-2.3", "status": "gap", "note": "Data classification incomplete for prompts"},
                {"control": "CC6.1", "status": "partial", "note": "Access reviews quarterly but AI roles omitted"},
            ],
            "confidence": 0.84,
        },
        "policy": {
            "summary": "3 policy violations: missing human-in-loop for high-risk answers; no approved-model list.",
            "violations": [
                {"id": "p1", "policy": "gie.ai.hitl.high-risk", "status": "fail"},
                {"id": "p2", "policy": "gie.ai.approved-models", "status": "fail"},
                {"id": "p3", "policy": "gie.data.retention.pii", "status": "warn"},
            ],
            "confidence": 0.87,
        },
        "recommendation": {
            "summary": "Prioritize prompt firewall, PII redaction, and model change control this sprint.",
            "actions": [
                {"id": "a1", "priority": 1, "title": "Add prompt-injection filter before LLM call"},
                {"id": "a2", "priority": 1, "title": "Redact email/phone in chat_history writes"},
                {"id": "a3", "priority": 2, "title": "Require eval suite pass before model upgrade"},
            ],
            "confidence": 0.9,
        },
        "generator": {
            "summary": "Drafted Guardrails policy pack v0.3 for ACME AI Assistant (3 policies, 2 monitors).",
            "artifacts": [
                {"type": "policy", "name": "acme-prompt-firewall.yaml"},
                {"type": "policy", "name": "acme-pii-redaction.yaml"},
                {"type": "monitor", "name": "acme-model-drift-check.yaml"},
            ],
            "confidence": 0.83,
        },
        "validation": {
            "summary": "Policy pack syntax valid; 2/3 policies pass dry-run against demo traces.",
            "results": [
                {"artifact": "acme-prompt-firewall.yaml", "status": "pass"},
                {"artifact": "acme-pii-redaction.yaml", "status": "pass"},
                {"artifact": "acme-model-drift-check.yaml", "status": "warn", "note": "Needs baseline metrics"},
            ],
            "confidence": 0.82,
        },
        "explainability": {
            "summary": "Risk elevated mainly due to unvalidated prompts and PII retention (62% of score weight).",
            "narrative": (
                f"For tenant {tenant} source {path}, GIE found an Azure OpenAI chat path without "
                "input validation. Combined with long retention of identifiable chat logs, residual "
                "risk remains elevated until firewall + redaction land."
            ),
            "drivers": [
                {"factor": "prompt_injection_exposure", "weight": 0.34},
                {"factor": "pii_retention", "weight": 0.28},
                {"factor": "model_change_control", "weight": 0.16},
            ],
            "confidence": 0.89,
        },
        "learning": {
            "summary": "Learning agent noted recurring PII pattern across last 3 ACME scans (demo).",
            "signals": [{"pattern": "email_in_prompts", "count": 3}],
            "confidence": 0.8,
        },
        "integration": {
            "summary": "Demo integrations ready: webhook + Jira ticket stubs for top actions.",
            "targets": [{"system": "jira", "project": "ACME-SEC"}, {"system": "webhook", "url": "https://example.invalid/gie"}],
            "confidence": 0.78,
        },
    }

    body = catalog.get(
        agent_id,
        {
            "summary": f"{agent_id} demo analysis complete",
            "confidence": 0.8,
        },
    )
    return {
        "agent_id": agent_id,
        "version": version,
        "status": "ok",
        "demo": True,
        "tenant_id": tenant,
        "source_path": path,
        "artifacts": {"id": art, **({"items": body.get("artifacts")} if "artifacts" in body else {})},
        **{k: v for k, v in body.items() if k != "artifacts"},
    }
