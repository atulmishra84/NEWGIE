"""Live peer HTTP calls for Orchestrator analyze steps."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import uuid4

import httpx
import jwt

from orchestrator.domain.retry import RetryableError
from orchestrator.settings import Settings


def _conf(value: Any, default: float = 0.75) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict) and value.get("score") is not None:
        try:
            return float(value["score"])
        except (TypeError, ValueError):
            return default
    return default


def _agent_name(source: dict[str, Any] | None, tenant_id: str) -> str:
    source = source or {}
    path = str(source.get("path") or "ai-system")
    leaf = path.rstrip("/").split("/")[-1] or "ai-system"
    return f"{tenant_id}-{leaf}"[:64]


def mint_service_token(settings: Settings, tenant_id: str) -> str:
    """JWT for peers that require auth (context-intelligence)."""
    secret = settings.jwt_secret or "local-dev-secret-change-me"
    now = int(time.time())
    payload = {
        "sub": "gie-orchestrator",
        "tenant_id": tenant_id,
        "roles": ["admin", "write", "read"],
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm or "HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def headers_for(settings: Settings, tenant_id: str, *, with_bearer: bool = False) -> dict[str, str]:
    h = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-tenant-id": tenant_id,
        "x-correlation-id": uuid4().hex,
    }
    if with_bearer:
        h["Authorization"] = f"Bearer {mint_service_token(settings, tenant_id)}"
    return h


def unwrap_data(body: Any) -> Any:
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
) -> Any:
    try:
        r = await client.request(method, url, headers=headers, json=json_body)
    except httpx.TimeoutException as exc:
        raise RetryableError(f"timeout calling {url}") from exc
    except httpx.HTTPError as exc:
        raise RetryableError(f"unavailable {url}: {exc}") from exc
    if r.status_code >= 500:
        raise RetryableError(f"{url} returned {r.status_code}: {r.text[:240]}")
    if r.status_code >= 400:
        raise RuntimeError(f"{url} returned {r.status_code}: {r.text[:400]}")
    if not r.content:
        return None
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {"raw": r.text}


def _source_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    inp = payload.get("input") or {}
    source = inp.get("source") or {}
    if not source and isinstance(inp.get("path"), str):
        source = {"type": "folder", "path": inp["path"]}
    if "type" not in source and source:
        source = {**source, "type": source.get("type") or "folder"}
    return source if isinstance(source, dict) else {"type": "folder", "path": str(source)}


def _upstream(payload: dict[str, Any], key: str) -> dict[str, Any]:
    up = payload.get("upstream") or {}
    val = up.get(key) or {}
    return val if isinstance(val, dict) else {}


# --- Normalizers (brief-friendly) -------------------------------------------------

def normalize_context(data: dict[str, Any], *, source: dict[str, Any]) -> dict[str, Any]:
    model = data.get("context_model") or data
    ai = model.get("ai") if isinstance(model, dict) else {}
    assets = []
    if isinstance(ai, dict):
        for m in ai.get("models") or []:
            if isinstance(m, dict):
                assets.append(
                    {
                        "id": m.get("id") or m.get("name") or "model",
                        "type": "model",
                        "name": m.get("name") or m.get("id") or "model",
                        "provider": m.get("provider") or m.get("vendor"),
                    }
                )
        for s in ai.get("services") or ai.get("apps") or []:
            if isinstance(s, dict):
                assets.append(
                    {
                        "id": s.get("id") or s.get("name") or "service",
                        "type": "service",
                        "name": s.get("name") or s.get("id") or "service",
                        "runtime": s.get("runtime") or s.get("language"),
                    }
                )
    if not assets:
        path = source.get("path") or "/unknown"
        assets = [
            {"id": "target", "type": "source", "name": str(path).rstrip("/").split("/")[-1], "runtime": source.get("type")},
        ]
    summary = data.get("summary")
    if not summary:
        summary = f"Live context scan of {source.get('path') or 'source'} found {len(assets)} component(s)."
        if data.get("scan_id"):
            summary += f" Scan {data['scan_id']} status={data.get('scan_status') or 'completed'}."
    return {
        "summary": summary,
        "assets": assets,
        "data_flows": data.get("data_flows") or [],
        "context_model": model if isinstance(model, dict) else {},
        "scan_id": data.get("scan_id"),
        "model_id": data.get("model_id"),
        "confidence": _conf(data.get("confidence") or (model.get("provenance") or {}).get("confidence") if isinstance(model, dict) else None, 0.8),
        "source_path": source.get("path"),
    }


def normalize_knowledge(data: dict[str, Any]) -> dict[str, Any]:
    hits = data.get("hits") or []
    frameworks = []
    for h in hits:
        node = (h.get("node") if isinstance(h, dict) else None) or h
        if isinstance(node, dict):
            title = node.get("title") or node.get("name")
            domain = node.get("domain")
            if domain and domain not in frameworks:
                frameworks.append(str(domain))
            elif title and title not in frameworks and len(frameworks) < 8:
                frameworks.append(str(title))
    evidence = []
    for h in hits[:5]:
        node = (h.get("node") if isinstance(h, dict) else None) or h
        if isinstance(node, dict):
            evidence.append(
                {
                    "id": node.get("id") or uuid4().hex[:8],
                    "title": node.get("title") or node.get("name") or "knowledge hit",
                    "severity": "medium",
                }
            )
    summary = data.get("summary") or (
        f"Knowledge query returned {len(hits)} hit(s)"
        + (f" across {', '.join(frameworks[:4])}" if frameworks else "")
        + "."
    )
    return {
        "summary": summary,
        "frameworks": frameworks,
        "evidence": evidence,
        "hits": hits[:12],
        "confidence": _conf(data.get("confidence"), 0.7),
    }


def normalize_risk(data: dict[str, Any]) -> dict[str, Any]:
    raw_score = data.get("overall_ai_risk_score")
    try:
        score_01 = float(raw_score) if raw_score is not None else 0.5
    except (TypeError, ValueError):
        score_01 = 0.5
    score_100 = int(round(score_01 * 100)) if score_01 <= 1.0 else int(round(score_01))
    findings = []
    for f in data.get("factors") or []:
        if not isinstance(f, dict):
            continue
        findings.append(
            {
                "id": f.get("factor_id") or uuid4().hex[:8],
                "title": f.get("name") or f.get("explanation") or "Risk factor",
                "severity": str(f.get("severity") or "medium").lower(),
                "likelihood": float(f.get("score") or 0.5),
            }
        )
    remediations = []
    for r in data.get("remediations") or []:
        if isinstance(r, dict):
            remediations.append({"id": r.get("action_id"), "title": r.get("title"), "priority": r.get("priority")})
    severity = str(data.get("severity") or "medium").lower()
    summary = (
        data.get("summary")
        or f"Overall AI risk score {score_100}/100 ({severity}). "
        f"{len(findings)} factor(s) evaluated from live Risk Intelligence."
    )
    return {
        "summary": summary,
        "score": score_100,
        "overall_ai_risk_score": score_01,
        "severity": severity,
        "trust_score": data.get("trust_score"),
        "findings": findings,
        "remediations": remediations,
        "category_scores": data.get("category_scores") or {},
        "confidence": _conf(data.get("confidence"), 0.75),
        "report_id": data.get("report_id"),
    }


def normalize_compliance(data: dict[str, Any]) -> dict[str, Any]:
    gaps = []
    for g in data.get("gaps") or []:
        if not isinstance(g, dict):
            continue
        gaps.append(
            {
                "control": g.get("control_id") or g.get("control") or g.get("framework") or "control",
                "status": g.get("status") or g.get("severity") or "gap",
                "note": g.get("description") or g.get("title") or g.get("note") or "",
            }
        )
    frameworks = []
    for f in data.get("applicable_frameworks") or []:
        if isinstance(f, dict) and f.get("applicable"):
            frameworks.append(str(f.get("framework")))
        elif isinstance(f, str):
            frameworks.append(f)
    score = data.get("compliance_score")
    try:
        score_f = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_f = None
    summary = data.get("summary") or (
        f"Compliance score {score_f:.0%}." if score_f is not None else "Compliance analysis completed."
    )
    if gaps:
        summary += f" {len(gaps)} gap(s) identified."
    return {
        "summary": summary,
        "compliance_score": score_f,
        "gaps": gaps,
        "frameworks": frameworks,
        "applicable_frameworks": data.get("applicable_frameworks") or [],
        "confidence": _conf(data.get("confidence"), 0.75),
        "report_id": data.get("report_id"),
    }


def normalize_policy(data: dict[str, Any]) -> dict[str, Any]:
    violations = []
    for r in data.get("recommendations") or []:
        if not isinstance(r, dict):
            continue
        # Policy agent returns recommendations; map to check-like rows for the brief
        violations.append(
            {
                "id": r.get("id") or uuid4().hex[:8],
                "policy": r.get("title") or r.get("control") or "policy-recommendation",
                "status": "warn" if str(r.get("priority", "")).lower() in {"low", "medium"} else "fail",
            }
        )
    artifacts = data.get("artifacts") or []
    summary = data.get("summary") or (
        f"Policy Intelligence produced {len(data.get('recommendations') or [])} recommendation(s) "
        f"and {len(artifacts)} artifact(s)."
    )
    return {
        "summary": summary,
        "violations": violations,
        "recommendations": data.get("recommendations") or [],
        "artifacts": artifacts[:8],
        "confidence": _conf(data.get("confidence"), 0.75),
        "decision_id": data.get("decision_id"),
    }


def normalize_recommendation(data: dict[str, Any]) -> dict[str, Any]:
    actions = []
    for i, r in enumerate(data.get("recommendations") or [], start=1):
        if not isinstance(r, dict):
            continue
        pr = r.get("priority") or "medium"
        # Map enum-ish priorities to numeric for the brief UI
        pr_map = {"critical": 1, "high": 1, "medium": 2, "low": 3}
        priority_num = pr_map.get(str(pr).lower(), 2)
        actions.append(
            {
                "id": r.get("recommendation_id") or f"a{i}",
                "priority": priority_num,
                "priority_label": str(pr),
                "title": r.get("title") or "Recommendation",
                "reason": r.get("reason"),
                "business_impact": r.get("business_impact"),
            }
        )
    summary = data.get("summary") or f"{len(actions)} prioritized recommendation(s) from live Recommendation Intelligence."
    return {
        "summary": summary,
        "actions": actions,
        "recommendations": data.get("recommendations") or [],
        "confidence": _conf(data.get("confidence"), 0.8),
        "report_id": data.get("report_id"),
    }


def normalize_generator(data: dict[str, Any]) -> dict[str, Any]:
    items = []
    for p in data.get("policies") or []:
        if not isinstance(p, dict):
            continue
        meta = p.get("metadata") or {}
        fmt = p.get("format") or "policy"
        name = meta.get("name") or f"{fmt}-policy"
        items.append({"type": str(fmt), "name": f"{name}.{fmt}" if "." not in str(name) else str(name)})
    for a in data.get("artifacts") or data.get("named_artifacts") or []:
        if isinstance(a, dict):
            items.append({"type": a.get("type") or a.get("format") or "artifact", "name": a.get("name") or a.get("filename") or "artifact"})
        elif isinstance(a, str):
            items.append({"type": "artifact", "name": a})
    summary = data.get("summary") or f"Generated policy package with {len(items)} artifact(s)."
    return {
        "summary": summary,
        "artifacts": {"id": str(data.get("package_id") or uuid4().hex[:10]), "items": items},
        "policies": data.get("policies") or [],
        "package_id": data.get("package_id"),
        "confidence": _conf(data.get("confidence"), 0.8),
    }


def normalize_validation(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for c in data.get("checks") or []:
        if not isinstance(c, dict):
            continue
        results.append(
            {
                "artifact": c.get("category") or "check",
                "status": c.get("verdict") or c.get("status") or "unknown",
                "note": c.get("message") or "",
            }
        )
    for f in data.get("findings") or []:
        if isinstance(f, dict):
            results.append(
                {
                    "artifact": f.get("path") or f.get("title") or "finding",
                    "status": f.get("verdict") or "failed",
                    "note": f.get("detail") or f.get("title") or "",
                }
            )
    summary = data.get("summary") or (
        f"Validation verdict={data.get('verdict')}, approval={data.get('approval_status')}."
    )
    return {
        "summary": summary,
        "verdict": data.get("verdict"),
        "approval_status": data.get("approval_status"),
        "results": results,
        "confidence": _conf(data.get("confidence"), 0.75),
        "validation_id": data.get("validation_id"),
    }


def normalize_explainability(data: dict[str, Any]) -> dict[str, Any]:
    dims = data.get("dimensions") or {}
    narrative = ""
    if isinstance(dims, dict):
        narrative = dims.get("why") or ""
    views = data.get("views") or {}
    if not narrative and isinstance(views, dict):
        for v in views.values():
            if isinstance(v, dict) and v.get("narrative"):
                narrative = v["narrative"]
                break
    drivers = []
    for i, step in enumerate(data.get("reasoning_path") or []):
        if isinstance(step, dict):
            drivers.append(
                {
                    "factor": step.get("action") or step.get("agent") or f"step_{i+1}",
                    "weight": max(0.05, 0.4 / (i + 1)),
                }
            )
    summary = data.get("summary") or "Explainability narrative generated from live pipeline outputs."
    return {
        "summary": summary,
        "narrative": narrative or summary,
        "drivers": drivers[:5],
        "dimensions": dims,
        "confidence": _conf(data.get("confidence"), 0.8),
        "explanation_id": data.get("explanation_id"),
    }


# --- Per-agent callers ------------------------------------------------------------

async def invoke_context(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    source = _source_from_payload(payload)
    # Prefer a path the sandbox worker can read when demo path is used
    path = str(source.get("path") or "")
    if path.startswith("/demo/"):
        source = {**source, "type": "folder", "path": f"/tmp{path}"}
    hdrs = headers_for(settings, tenant, with_bearer=True)
    created = unwrap_data(
        await _request(
            client,
            "POST",
            f"{base}/v1/scans",
            headers=hdrs,
            json_body={"source": source},
        )
    )
    scan_id = (created or {}).get("scan_id")
    if not scan_id:
        return normalize_context({"summary": "Context scan could not be created.", **(created or {})}, source=source)

    # Prefer the step HTTP timeout (context steps are 45s in the default graph).
    try:
        client_budget = float(client.timeout.read)  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        client_budget = settings.default_step_timeout_ms / 1000.0
    deadline = time.monotonic() + max(20.0, min(40.0, client_budget * 0.85))
    scan = created or {}
    while time.monotonic() < deadline:
        scan = unwrap_data(await _request(client, "GET", f"{base}/v1/scans/{scan_id}", headers=hdrs)) or {}
        status = str(scan.get("status") or "")
        if status in {"completed", "failed", "cancelled"}:
            break
        await asyncio.sleep(1.0)

    model = None
    model_id = scan.get("model_id")
    if model_id and str(scan.get("status")) == "completed":
        try:
            model = unwrap_data(await _request(client, "GET", f"{base}/v1/context-models/{model_id}", headers=hdrs))
        except Exception:  # noqa: BLE001
            model = None

    packed = {
        "scan_id": scan_id,
        "scan_status": scan.get("status"),
        "model_id": model_id,
        "context_model": model or {},
        "error_message": scan.get("error_message"),
    }
    if str(scan.get("status")) != "completed":
        packed["summary"] = (
            f"Live context scan {scan_id} ended as {scan.get('status')}"
            + (f": {scan.get('error_message')}" if scan.get("error_message") else ".")
        )
    return normalize_context(packed, source=_source_from_payload(payload))


async def invoke_knowledge(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    source = _source_from_payload(payload)
    ctx = _upstream(payload, "context")
    query = (
        f"AI governance risks for {source.get('path') or 'application'}: "
        "prompt injection, PII retention, model change control, NIST AI RMF, SOC2"
    )
    body = {
        "query": query,
        "top_k": 8,
        "include_evidence": True,
        "include_graph": False,
        "hybrid": True,
    }
    try:
        data = unwrap_data(
            await _request(client, "POST", f"{base}/v1/knowledge/query", headers=headers_for(settings, tenant), json_body=body)
        )
        return normalize_knowledge(data or {})
    except Exception as exc:  # noqa: BLE001
        # Knowledge graph may be empty in fresh sandboxes
        return {
            "summary": f"Knowledge query unavailable ({exc}); continuing with declared frameworks.",
            "frameworks": ["nist_ai_rmf", "soc2", "iso27001"],
            "evidence": [],
            "confidence": 0.55,
            "live_error": str(exc)[:240],
            "context_hint": ctx.get("summary"),
        }


async def invoke_risk(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    source = _source_from_payload(payload)
    ctx = _upstream(payload, "context")
    knowledge = _upstream(payload, "knowledge")
    body = {
        "bundle": {
            "tenant_id": tenant,
            "agent_id": _agent_name(source, tenant),
            "context_model": ctx.get("context_model") or {"source": source, "assets": ctx.get("assets") or []},
            "knowledge_graph": {"frameworks": knowledge.get("frameworks") or [], "hits": knowledge.get("hits") or []},
            "ai_models": [a for a in (ctx.get("assets") or []) if a.get("type") == "model"],
        },
        "persist": False,
    }
    data = unwrap_data(
        await _request(client, "POST", f"{base}/v1/risk/calculate", headers=headers_for(settings, tenant), json_body=body)
    )
    return normalize_risk(data or {})


async def invoke_compliance(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    source = _source_from_payload(payload)
    ctx = _upstream(payload, "context")
    risk = _upstream(payload, "risk")
    knowledge = _upstream(payload, "knowledge")
    frameworks = knowledge.get("frameworks") or ["nist_ai_rmf", "soc2"]
    # Map free-text / domain names to contract enums where possible
    declared = []
    for f in frameworks:
        key = str(f).lower().replace("-", "_").replace(" ", "_")
        if "nist" in key:
            declared.append("nist_ai_rmf")
        elif "soc" in key:
            declared.append("soc2")
        elif "iso" in key:
            declared.append("iso27001")
        elif "gdpr" in key:
            declared.append("gdpr")
        elif key in {"hipaa", "gdpr", "pci_dss", "soc2", "iso27001", "nist_ai_rmf", "eu_ai_act"}:
            declared.append(key)
    if not declared:
        declared = ["nist_ai_rmf", "soc2"]
    body = {
        "bundle": {
            "tenant_id": tenant,
            "application_id": _agent_name(source, tenant),
            "context_model": ctx.get("context_model") or {"source": source, "assets": ctx.get("assets") or []},
            "risk_report": {
                "overall_ai_risk_score": risk.get("overall_ai_risk_score") or ((risk.get("score") or 50) / 100.0),
                "severity": risk.get("severity") or "medium",
                "findings": risk.get("findings") or [],
            },
            "knowledge": knowledge,
            "declared_frameworks": list(dict.fromkeys(declared))[:8],
        },
        "persist": False,
    }
    data = unwrap_data(
        await _request(client, "POST", f"{base}/v1/compliance/analyze", headers=headers_for(settings, tenant), json_body=body)
    )
    return normalize_compliance(data or {})


async def invoke_policy(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    body = {
        "bundle": {
            "tenant_id": tenant,
            "context": _upstream(payload, "context"),
            "risk": _upstream(payload, "risk"),
            "compliance": _upstream(payload, "compliance"),
            "knowledge": _upstream(payload, "knowledge"),
            "targets": ["openai"],
            "formats": ["yaml", "json"],
        },
        "dry_run": True,
    }
    data = unwrap_data(
        await _request(client, "POST", f"{base}/v1/policies/generate", headers=headers_for(settings, tenant), json_body=body)
    )
    return normalize_policy(data or {})


async def invoke_recommendation(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    source = _source_from_payload(payload)
    risk = _upstream(payload, "risk")
    compliance = _upstream(payload, "compliance")
    body = {
        "bundle": {
            "tenant_id": tenant,
            "agent_id": _agent_name(source, tenant),
            "risk": {
                "overall_ai_risk_score": risk.get("score") or int(round(float(risk.get("overall_ai_risk_score") or 0.5) * 100)),
                "severity": risk.get("severity") or "medium",
                "findings": risk.get("findings") or [],
            },
            "compliance": {
                "compliance_score": compliance.get("compliance_score") or 0.5,
                "gaps": compliance.get("gaps") or [],
            },
            "context": _upstream(payload, "context"),
            "knowledge": _upstream(payload, "knowledge"),
            "policies": _upstream(payload, "policy"),
        },
        "persist": False,
    }
    data = unwrap_data(
        await _request(client, "POST", f"{base}/v1/recommendations", headers=headers_for(settings, tenant), json_body=body)
    )
    return normalize_recommendation(data or {})


async def invoke_generator(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    source = _source_from_payload(payload)
    rec = _upstream(payload, "recommendation")
    recommendations = rec.get("recommendations") or [
        {"title": a.get("title"), "priority": a.get("priority_label") or f"P{a.get('priority', 2)}"}
        for a in (rec.get("actions") or [])
    ]
    body = {
        "bundle": {
            "tenant_id": tenant,
            "agent_id": _agent_name(source, tenant),
            "recommendations": recommendations[:12],
            "risk": _upstream(payload, "risk"),
            "compliance": _upstream(payload, "compliance"),
            "formats": ["yaml", "json"],
        },
        "persist": False,
    }
    data = unwrap_data(
        await _request(client, "POST", f"{base}/v1/policy/generate", headers=headers_for(settings, tenant), json_body=body)
    )
    return normalize_generator(data or {})


async def invoke_validation(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    gen = _upstream(payload, "generator")
    policies = []
    for p in gen.get("policies") or []:
        if isinstance(p, dict):
            content = p.get("content")
            if content is None and isinstance(p.get("body"), dict):
                import json as _json

                content = _json.dumps(p["body"])
            policies.append(
                {
                    "name": (p.get("metadata") or {}).get("name") or "generated-policy",
                    "format": p.get("format") or "yaml",
                    "content": content or "",
                }
            )
    if not policies:
        for item in (gen.get("artifacts") or {}).get("items") or []:
            if isinstance(item, dict):
                policies.append({"name": item.get("name") or "artifact", "format": "yaml", "content": "apiVersion: gie.ai/v1\nkind: GuardrailsPolicy\n"})
    body = {
        "bundle": {
            "tenant_id": tenant,
            "agent_id": _agent_name(_source_from_payload(payload), tenant),
            "policy_package": gen,
            "policies": policies,
            "risk": _upstream(payload, "risk"),
            "compliance": _upstream(payload, "compliance"),
        },
        "persist": False,
        "run_simulation": False,
    }
    data = unwrap_data(
        await _request(client, "POST", f"{base}/v1/validate", headers=headers_for(settings, tenant), json_body=body)
    )
    return normalize_validation(data or {})


async def invoke_explainability(client: httpx.AsyncClient, base: str, settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = payload.get("tenant_id") or "default"
    risk = _upstream(payload, "risk")
    rec = _upstream(payload, "recommendation")
    body = {
        "bundle": {
            "tenant_id": tenant,
            "subject_type": "risk_report",
            "subject": {
                "score": risk.get("score"),
                "severity": risk.get("severity"),
                "summary": risk.get("summary"),
            },
            "recommendations": rec.get("recommendations") or rec.get("actions") or [],
            "risk": risk,
            "compliance": _upstream(payload, "compliance"),
            "policy_package": _upstream(payload, "generator"),
            "audiences": ["executive", "security", "developer"],
            "formats": ["markdown", "json"],
        },
        "persist": False,
    }
    data = unwrap_data(
        await _request(client, "POST", f"{base}/v1/explain", headers=headers_for(settings, tenant), json_body=body)
    )
    return normalize_explainability(data or {})


LIVE_HANDLERS = {
    "context": invoke_context,
    "knowledge": invoke_knowledge,
    "risk": invoke_risk,
    "compliance": invoke_compliance,
    "policy": invoke_policy,
    "recommendation": invoke_recommendation,
    "generator": invoke_generator,
    "validation": invoke_validation,
    "explainability": invoke_explainability,
}


async def live_invoke_agent(
    *,
    agent_id: str,
    version: str,
    base_url: str,
    payload: dict[str, Any],
    settings: Settings,
    timeout_ms: int,
) -> dict[str, Any]:
    handler = LIVE_HANDLERS.get(agent_id)
    if handler is None:
        raise RuntimeError(f"No live handler registered for agent '{agent_id}'")
    timeout = max(5.0, timeout_ms / 1000.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Preflight health
        try:
            hr = await client.get(f"{base_url}/healthz")
            if hr.status_code >= 500:
                raise RetryableError(f"{agent_id} unhealthy: {hr.status_code}")
        except httpx.TimeoutException as exc:
            raise RetryableError(f"{agent_id} health timeout") from exc
        except httpx.HTTPError as exc:
            raise RetryableError(f"{agent_id} unavailable: {exc}") from exc

        out = await handler(client, base_url.rstrip("/"), settings, payload)
    out = dict(out or {})
    out.update(
        {
            "agent_id": agent_id,
            "version": version,
            "status": "ok",
            "live": True,
            "peer_base_url": base_url,
            "peer_healthy": True,
            "demo": False,
        }
    )
    if "confidence" not in out or not isinstance(out["confidence"], (int, float)):
        out["confidence"] = _conf(out.get("confidence"), 0.75)
    return out
