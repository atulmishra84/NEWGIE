"""Policy validation engine: checks, simulation, approval status."""

from __future__ import annotations

import json
import time
from typing import Any

import yaml

from gie_contracts.validation import (
    ApprovalStatus,
    CheckCategory,
    CheckResult,
    Confidence,
    CorrectionRecommendation,
    ValidationFinding,
    ValidationInputBundle,
    ValidationReport,
    ValidationVerdict,
    SimulateRequest,
)

from validation_intelligence.domain.extract import collect_documents, extract_rules
from validation_intelligence.domain.simulate import run_simulations
from validation_intelligence.version import AGENT_VERSION


def _worst(a: ValidationVerdict, b: ValidationVerdict) -> ValidationVerdict:
    order = {
        ValidationVerdict.PASS: 0,
        ValidationVerdict.WARNING: 1,
        ValidationVerdict.FAILED: 2,
    }
    return a if order[a] >= order[b] else b


def _finding(
    cat: CheckCategory,
    verdict: ValidationVerdict,
    title: str,
    detail: str,
    path: str | None = None,
    evidence: list[str] | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        category=cat,
        verdict=verdict,
        title=title,
        detail=detail,
        path=path,
        evidence=evidence or [],
    )


def check_syntax(docs: list[dict[str, Any]]) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    for d in docs:
        content = d.get("content") or ""
        fname = d.get("filename") or "unknown"
        fmt = str(d.get("format") or "").lower()
        if d.get("parse_error"):
            findings.append(
                _finding(
                    CheckCategory.SYNTAX,
                    ValidationVerdict.FAILED,
                    f"Parse error in {fname}",
                    str(d["parse_error"]),
                    fname,
                )
            )
            continue
        if not content.strip() and fname != "empty":
            findings.append(
                _finding(
                    CheckCategory.SYNTAX,
                    ValidationVerdict.FAILED,
                    f"Empty content {fname}",
                    "Artifact has no content",
                    fname,
                )
            )
        if fmt in {"opa_rego", "rego"} or fname.endswith(".rego"):
            if "package " not in content:
                findings.append(
                    _finding(
                        CheckCategory.SYNTAX,
                        ValidationVerdict.FAILED,
                        "Rego missing package",
                        "OPA policies require a package declaration",
                        fname,
                    )
                )
            if "allow" not in content and "deny" not in content:
                findings.append(
                    _finding(
                        CheckCategory.SYNTAX,
                        ValidationVerdict.WARNING,
                        "Rego missing allow/deny",
                        "No allow/deny rules found",
                        fname,
                    )
                )
        if fmt == "terraform" or fname.endswith(".tf"):
            if "resource" not in content and "terraform" not in content:
                findings.append(
                    _finding(
                        CheckCategory.SYNTAX,
                        ValidationVerdict.FAILED,
                        "Invalid Terraform",
                        "No terraform/resource blocks",
                        fname,
                    )
                )
        if fmt in {"yaml", "kubernetes", "admission_controller"} or fname.endswith(
            (".yaml", ".yml")
        ):
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as exc:
                findings.append(
                    _finding(
                        CheckCategory.SYNTAX,
                        ValidationVerdict.FAILED,
                        "YAML syntax error",
                        str(exc),
                        fname,
                    )
                )
        if content.lstrip().startswith("{") or fmt.endswith("json") or "json" in fmt:
            try:
                if content.strip():
                    json.loads(content)
            except json.JSONDecodeError as exc:
                findings.append(
                    _finding(
                        CheckCategory.SYNTAX,
                        ValidationVerdict.FAILED,
                        "JSON syntax error",
                        str(exc),
                        fname,
                    )
                )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.SYNTAX,
        verdict=verdict,
        message=f"Syntax check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def check_schema(docs: list[dict[str, Any]]) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    for d in docs:
        body = d.get("body") or {}
        fname = d["filename"]
        if body.get("_parse_error"):
            findings.append(
                _finding(
                    CheckCategory.SCHEMA,
                    ValidationVerdict.FAILED,
                    "Schema unreadable",
                    "Cannot validate schema due to parse failure",
                    fname,
                )
            )
            continue
        # lightweight schema expectations by kind
        if isinstance(body, dict) and body.get("kind") in {
            "GuardrailsPolicy",
            "NetworkPolicy",
            "ValidatingAdmissionPolicy",
        }:
            if not body.get("apiVersion"):
                findings.append(
                    _finding(
                        CheckCategory.SCHEMA,
                        ValidationVerdict.FAILED,
                        "Missing apiVersion",
                        "Kubernetes-style docs require apiVersion",
                        fname,
                    )
                )
            if not body.get("metadata"):
                findings.append(
                    _finding(
                        CheckCategory.SCHEMA,
                        ValidationVerdict.WARNING,
                        "Missing metadata",
                        "metadata block recommended",
                        fname,
                    )
                )
        if fname == "openai-policy.json" and isinstance(body, dict):
            if body.get("object") != "guardrails.policy" and "steps" not in body:
                findings.append(
                    _finding(
                        CheckCategory.SCHEMA,
                        ValidationVerdict.WARNING,
                        "OpenAI schema drift",
                        "Expected object=guardrails.policy or steps[]",
                        fname,
                    )
                )
        if fname == "azure-foundry-policy.json" and isinstance(body, dict):
            if "contentFilters" not in body and "schema" not in body:
                findings.append(
                    _finding(
                        CheckCategory.SCHEMA,
                        ValidationVerdict.WARNING,
                        "Foundry schema incomplete",
                        "contentFilters recommended",
                        fname,
                    )
                )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.SCHEMA,
        verdict=verdict,
        message=f"Schema check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def check_compliance(
    bundle: ValidationInputBundle, docs: list[dict[str, Any]]
) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    gaps = bundle.compliance.get("gaps") or []
    critical_gaps = [
        g
        for g in gaps
        if isinstance(g, dict)
        and str(g.get("severity", "")).lower() in {"critical", "high"}
    ]
    controls: set[str] = set()
    for d in docs:
        body = d.get("body") or {}
        for c in body.get("controls") or (body.get("spec") or {}).get("controls") or []:
            controls.add(str(c))
        rules = body.get("rules") or (body.get("spec") or {}).get("rules") or {}
        if isinstance(rules, dict) and rules.get("redact_pii"):
            controls.add("gr-pii-presidio")
        if isinstance(rules, dict) and rules.get("block_prompt_injection"):
            controls.add("gr-prompt-firewall")
    for g in critical_gaps[:8]:
        cid = str(g.get("control_id") or g.get("title") or "gap")
        # if privacy/phi gap and no pii control
        if (
            any(x in cid.lower() for x in ("phi", "pii", "gdpr", "hipaa"))
            and "gr-pii-presidio" not in controls
            and not any("pii" in c for c in controls)
        ):
            findings.append(
                _finding(
                    CheckCategory.COMPLIANCE,
                    ValidationVerdict.FAILED,
                    f"Unresolved compliance gap {cid}",
                    "Policy package does not clearly address this gap",
                    evidence=[cid],
                )
            )
        elif critical_gaps and not controls:
            findings.append(
                _finding(
                    CheckCategory.COMPLIANCE,
                    ValidationVerdict.WARNING,
                    f"Gap {cid} not mapped",
                    "No controls detected in policies",
                    evidence=[cid],
                )
            )
    if (
        bundle.compliance.get("compliance_score") is not None
        and float(bundle.compliance["compliance_score"]) < 0.4
        and not findings
    ):
        findings.append(
            _finding(
                CheckCategory.COMPLIANCE,
                ValidationVerdict.WARNING,
                "Low compliance score",
                f"score={bundle.compliance['compliance_score']}",
            )
        )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.COMPLIANCE,
        verdict=verdict,
        message=f"Compliance check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def check_runtime(
    bundle: ValidationInputBundle, docs: list[dict[str, Any]]
) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    runtime = bundle.runtime or {}
    exposure = str(
        runtime.get("exposure")
        or (bundle.context.get("deployment") or {}).get("exposure")
        or ""
    ).lower()
    has_rate = False
    has_opa = False
    for d in docs:
        body = d.get("body") or {}
        rules = body.get("rules") or (body.get("spec") or {}).get("rules") or {}
        if isinstance(rules, dict) and rules.get("rate_limit"):
            has_rate = True
        if (
            d["filename"].endswith(".rego")
            or body.get("opa_package")
            or body.get("type") == "runtime_policy"
        ):
            has_opa = True
        if body.get("rate_limit", {}).get("enabled"):
            has_rate = True
    if exposure == "public" and not has_rate:
        findings.append(
            _finding(
                CheckCategory.RUNTIME_COMPATIBILITY,
                ValidationVerdict.WARNING,
                "Public exposure without rate limit",
                "Add rate limiting for public agents",
            )
        )
    if not has_opa and any(str(d.get("format")) == "runtime" for d in docs) is False:
        # soft warning only when runtime config claims enforce
        if runtime.get("enforce") and not has_opa:
            findings.append(
                _finding(
                    CheckCategory.RUNTIME_COMPATIBILITY,
                    ValidationVerdict.FAILED,
                    "Runtime enforce without OPA",
                    "enforce=true but no OPA/runtime policy present",
                )
            )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.RUNTIME_COMPATIBILITY,
        verdict=verdict,
        message=f"Runtime check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def check_conflicts_and_duplicates(
    docs: list[dict[str, Any]],
) -> tuple[CheckResult, CheckResult]:
    started = time.perf_counter()
    rules = extract_rules(docs)
    by_id: dict[str, list[Any]] = {}
    for r in rules:
        by_id.setdefault(str(r["id"]), []).append(r)
    dup_findings: list[ValidationFinding] = []
    conflict_findings: list[ValidationFinding] = []
    for rid, items in by_id.items():
        if len(items) > 1:
            values = [
                json.dumps(i["value"], sort_keys=True, default=str) for i in items
            ]
            if len(set(values)) == 1:
                dup_findings.append(
                    _finding(
                        CheckCategory.DUPLICATE_RULES,
                        ValidationVerdict.WARNING,
                        f"Duplicate rule {rid}",
                        f"Defined in {[i['source'] for i in items]}",
                        evidence=values,
                    )
                )
            else:
                conflict_findings.append(
                    _finding(
                        CheckCategory.POLICY_CONFLICTS,
                        ValidationVerdict.FAILED,
                        f"Conflicting rule {rid}",
                        f"Divergent values across {[i['source'] for i in items]}",
                        evidence=values,
                    )
                )
    # allow vs deny semantic conflict in rego
    for d in docs:
        content = d.get("content") or ""
        if (
            "default allow = true" in content
            and "deny {" in content
            and "default allow = false" not in content
        ):
            conflict_findings.append(
                _finding(
                    CheckCategory.POLICY_CONFLICTS,
                    ValidationVerdict.WARNING,
                    "Permissive default allow",
                    "default allow=true with deny rules may be hard to reason about",
                    d["filename"],
                )
            )
    dup_v = ValidationVerdict.PASS
    for f in dup_findings:
        dup_v = _worst(dup_v, f.verdict)
    conf_v = ValidationVerdict.PASS
    for f in conflict_findings:
        conf_v = _worst(conf_v, f.verdict)
    ms = int((time.perf_counter() - started) * 1000)
    return (
        CheckResult(
            category=CheckCategory.POLICY_CONFLICTS,
            verdict=conf_v,
            message=f"Conflict check: {conf_v.value}",
            findings=conflict_findings,
            duration_ms=ms,
        ),
        CheckResult(
            category=CheckCategory.DUPLICATE_RULES,
            verdict=dup_v,
            message=f"Duplicate check: {dup_v.value}",
            findings=dup_findings,
            duration_ms=ms,
        ),
    )


def check_performance(docs: list[dict[str, Any]]) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    total = sum(len(d.get("content") or "") for d in docs)
    if total > 500_000:
        findings.append(
            _finding(
                CheckCategory.PERFORMANCE,
                ValidationVerdict.WARNING,
                "Large policy bundle",
                f"Total bytes={total}; may slow admission/evaluation",
            )
        )
    for d in docs:
        content = d.get("content") or ""
        if content.count("deny {") > 50:
            findings.append(
                _finding(
                    CheckCategory.PERFORMANCE,
                    ValidationVerdict.WARNING,
                    "Many Rego deny rules",
                    "Consider consolidating rules",
                    d["filename"],
                )
            )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.PERFORMANCE,
        verdict=verdict,
        message=f"Performance check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def check_security(docs: list[dict[str, Any]]) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    for d in docs:
        content = (d.get("content") or "").lower()
        fname = d["filename"]
        if (
            "allow_all" in content
            or "disable_guardrails" in content
            or "permissive: true" in content
        ):
            findings.append(
                _finding(
                    CheckCategory.SECURITY,
                    ValidationVerdict.FAILED,
                    "Insecure permissive setting",
                    "Detected allow-all / disabled guardrails",
                    fname,
                    evidence=["permissive marker"],
                )
            )
        if "api_key" in content and "sk-" in content:
            findings.append(
                _finding(
                    CheckCategory.SECURITY,
                    ValidationVerdict.FAILED,
                    "Secret material in policy",
                    "Possible API key embedded in policy artifact",
                    fname,
                )
            )
        body = d.get("body") or {}
        rules = body.get("rules") or (body.get("spec") or {}).get("rules") or {}
        if (
            isinstance(rules, dict)
            and rules.get("tool_allowlist") is False
            and rules.get("require_human_approval") is False
        ):
            findings.append(
                _finding(
                    CheckCategory.SECURITY,
                    ValidationVerdict.WARNING,
                    "Unrestricted tools",
                    "tool_allowlist disabled without human approval",
                    fname,
                )
            )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.SECURITY,
        verdict=verdict,
        message=f"Security check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def check_framework_compat(
    bundle: ValidationInputBundle, docs: list[dict[str, Any]]
) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    ctx_fw = []
    for f in (bundle.context.get("ai") or {}).get("frameworks") or []:
        if isinstance(f, dict):
            ctx_fw.append(str(f.get("name") or "").lower())
        else:
            ctx_fw.append(str(f).lower())
    ctx_fw.extend(str(x).lower() for x in bundle.frameworks)
    filenames = {d["filename"] for d in docs}
    mapping = {
        "langgraph": "langgraph-policy.json",
        "crewai": "crewai-policy.json",
        "autogen": "autogen-policy.json",
        "semantic_kernel": "semantic-kernel-policy.json",
        "openai": "openai-policy.json",
    }
    for fw, needed in mapping.items():
        if (
            any(fw in x for x in ctx_fw)
            and needed not in filenames
            and not any(fw in d["filename"] for d in docs)
        ):
            findings.append(
                _finding(
                    CheckCategory.FRAMEWORK_COMPATIBILITY,
                    ValidationVerdict.WARNING,
                    f"Missing {fw} policy",
                    f"Context uses {fw} but {needed} not present",
                    evidence=ctx_fw,
                )
            )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.FRAMEWORK_COMPATIBILITY,
        verdict=verdict,
        message=f"Framework check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def check_model_compat(
    bundle: ValidationInputBundle, docs: list[dict[str, Any]]
) -> CheckResult:
    started = time.perf_counter()
    findings: list[ValidationFinding] = []
    models = list(bundle.models)
    for m in (bundle.context.get("ai") or {}).get("models") or []:
        if isinstance(m, dict):
            models.append(m)
    names = [str(m.get("name") if isinstance(m, dict) else m).lower() for m in models]
    has_openai_policy = any("openai" in d["filename"] for d in docs)
    if any("gpt" in n or "openai" in n for n in names) and not has_openai_policy:
        findings.append(
            _finding(
                CheckCategory.MODEL_COMPATIBILITY,
                ValidationVerdict.WARNING,
                "OpenAI model without openai policy",
                f"models={names[:5]}",
            )
        )
    if (
        any("claude" in n for n in names)
        and has_openai_policy
        and not any("anthropic" in d["filename"] for d in docs)
    ):
        findings.append(
            _finding(
                CheckCategory.MODEL_COMPATIBILITY,
                ValidationVerdict.WARNING,
                "Claude model with OpenAI-only policies",
                "Verify vendor-native filters apply",
                evidence=names[:5],
            )
        )
    verdict = ValidationVerdict.PASS
    for f in findings:
        verdict = _worst(verdict, f.verdict)
    return CheckResult(
        category=CheckCategory.MODEL_COMPATIBILITY,
        verdict=verdict,
        message=f"Model check: {verdict.value}",
        findings=findings,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def _corrections(findings: list[ValidationFinding]) -> list[CorrectionRecommendation]:
    out: list[CorrectionRecommendation] = []
    for f in findings:
        if f.verdict == ValidationVerdict.PASS:
            continue
        fix = None
        if f.category == CheckCategory.SYNTAX and "Rego missing package" in f.title:
            fix = "package gie.guardrails\n\ndefault allow = false\n"
        if f.category == CheckCategory.SECURITY and "permissive" in f.title.lower():
            fix = {"rules": {"tool_allowlist": True, "require_human_approval": True}}
        if (
            f.category == CheckCategory.RUNTIME_COMPATIBILITY
            and "rate limit" in f.title.lower()
        ):
            fix = {"rules": {"rate_limit": True}}
        out.append(
            CorrectionRecommendation(
                title=f"Fix: {f.title}",
                description=f.detail,
                severity="high" if f.verdict == ValidationVerdict.FAILED else "medium",
                category=f.category,
                target_path=f.path,
                suggested_fix=fix,
            )
        )
    return out[:40]


def _approval(verdict: ValidationVerdict) -> ApprovalStatus:
    if verdict == ValidationVerdict.FAILED:
        return ApprovalStatus.REJECTED
    if verdict == ValidationVerdict.WARNING:
        return ApprovalStatus.APPROVED_WITH_WARNINGS
    return ApprovalStatus.APPROVED


def validate_policies(
    bundle: ValidationInputBundle, *, run_simulation: bool = True
) -> ValidationReport:
    docs = collect_documents(bundle)
    reasoning = [
        {
            "step": 1,
            "action": "collect_documents",
            "detail": f"Loaded {len(docs)} policy documents",
        }
    ]
    checks: list[CheckResult] = []
    checks.append(check_syntax(docs))
    checks.append(check_schema(docs))
    checks.append(check_compliance(bundle, docs))
    checks.append(check_runtime(bundle, docs))
    conflict, dup = check_conflicts_and_duplicates(docs)
    checks.extend([conflict, dup])
    checks.append(check_performance(docs))
    checks.append(check_security(docs))
    checks.append(check_framework_compat(bundle, docs))
    checks.append(check_model_compat(bundle, docs))

    simulations = []
    if run_simulation:
        simulations = run_simulations(
            docs, bundle.simulation_scenarios or None, bundle.runtime
        )
        failed = [s for s in simulations if not s.passed]
        sim_findings = [
            _finding(
                CheckCategory.SIMULATION,
                ValidationVerdict.FAILED if not s.passed else ValidationVerdict.PASS,
                f"Scenario {s.scenario_name}",
                s.summary,
            )
            for s in simulations
            if not s.passed
        ]
        sim_verdict = ValidationVerdict.FAILED if failed else ValidationVerdict.PASS
        checks.append(
            CheckResult(
                category=CheckCategory.SIMULATION,
                verdict=sim_verdict,
                message=f"Simulation: {len(simulations) - len(failed)}/{len(simulations)} passed",
                findings=sim_findings,
            )
        )
        reasoning.append(
            {
                "step": 2,
                "action": "simulate",
                "detail": f"{len(simulations)} scenarios, failed={len(failed)}",
            }
        )

    findings = [f for c in checks for f in c.findings]
    verdict = ValidationVerdict.PASS
    for c in checks:
        verdict = _worst(verdict, c.verdict)
    invalid = [
        f"{f.category.value}:{f.title}"
        for f in findings
        if f.verdict == ValidationVerdict.FAILED
    ]
    corrections = _corrections(findings)
    approval = _approval(verdict)
    counts = {
        "checks": len(checks),
        "findings": len(findings),
        "failed": sum(1 for f in findings if f.verdict == ValidationVerdict.FAILED),
        "warnings": sum(1 for f in findings if f.verdict == ValidationVerdict.WARNING),
        "simulations": len(simulations),
        "corrections": len(corrections),
    }
    reasoning.append(
        {
            "step": len(reasoning) + 1,
            "action": "aggregate",
            "detail": f"verdict={verdict.value} approval={approval.value}",
        }
    )
    conf = (
        0.92
        if verdict == ValidationVerdict.PASS
        else 0.8
        if verdict == ValidationVerdict.WARNING
        else 0.7
    )
    return ValidationReport(
        tenant_id=bundle.tenant_id,
        agent_id=bundle.agent_id,
        agent_version=AGENT_VERSION,
        verdict=verdict,
        approval_status=approval,
        checks=checks,
        findings=findings,
        corrections=corrections,
        simulations=simulations,
        invalid_configurations=invalid,
        confidence=Confidence(
            score=conf, rationale="Deterministic multi-check validation"
        ),
        reasoning_path=reasoning,
        summary=f"Validation {verdict.value}; approval={approval.value}; findings={counts['findings']} (failed={counts['failed']}, warnings={counts['warnings']})",
        counts=counts,
    )


def simulate_only(request: SimulateRequest) -> ValidationReport:
    bundle = ValidationInputBundle(
        tenant_id=request.tenant_id,
        agent_id=request.agent_id,
        policy_package=request.policy_package,
        policies=request.policies,
        artifacts=request.artifacts,
        content=request.content,
        runtime=request.runtime,
        simulation_scenarios=request.scenarios,
    )
    return validate_policies(bundle, run_simulation=True)
