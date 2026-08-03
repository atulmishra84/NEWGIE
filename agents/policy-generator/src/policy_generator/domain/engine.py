"""Generate and validate deployment-ready policy packages from recommendations."""

from __future__ import annotations

import json
from typing import Any

import yaml

from gie_contracts.policy_generator import (
    Confidence,
    PolicyFormat,
    PolicyGeneratorInputBundle,
    PolicyPackage,
    RollbackPlan,
    ValidationResult,
    ValidationStatus,
    utcnow,
)

from policy_generator.domain.generators.render import ALL_FORMATS, render_policy
from policy_generator.version import AGENT_VERSION

# Default formats always produced (mission named artifacts + full suite)
DEFAULT_FORMATS = [
    PolicyFormat.YAML,
    PolicyFormat.JSON,
    PolicyFormat.OPA_REGO,
    PolicyFormat.AZURE_AI_FOUNDRY,
    PolicyFormat.OPENAI_GUARDRAILS,
    PolicyFormat.LANGGRAPH,
    PolicyFormat.CREWAI,
    PolicyFormat.AUTOGEN,
    PolicyFormat.SEMANTIC_KERNEL,
    PolicyFormat.NVIDIA_NEMO,
    PolicyFormat.TERRAFORM,
    PolicyFormat.KUBERNETES,
    PolicyFormat.ADMISSION_CONTROLLER,
    PolicyFormat.API_GATEWAY,
    PolicyFormat.PROMPT,
    PolicyFormat.IDENTITY,
    PolicyFormat.RUNTIME,
    PolicyFormat.DLP,
]


def _normalize_recs(bundle: PolicyGeneratorInputBundle) -> list[dict[str, Any]]:
    recs = list(bundle.recommendations or [])
    # Also accept nested recommendation report shape
    if not recs and isinstance(bundle.policies, dict):
        nested = bundle.policies.get("recommendations") or []
        if isinstance(nested, list):
            recs = nested
    return [r if isinstance(r, dict) else {"title": str(r)} for r in recs]


def generate_policy_package(
    bundle: PolicyGeneratorInputBundle,
    *,
    previous: PolicyPackage | None = None,
) -> PolicyPackage:
    recs = _normalize_recs(bundle)
    formats = list(bundle.formats) if bundle.formats else list(DEFAULT_FORMATS)
    # Ensure mission-critical named artifacts always present
    for required in (
        PolicyFormat.YAML,
        PolicyFormat.JSON,
        PolicyFormat.OPA_REGO,
        PolicyFormat.AZURE_AI_FOUNDRY,
        PolicyFormat.OPENAI_GUARDRAILS,
    ):
        if required not in formats:
            formats.append(required)

    reasoning: list[dict[str, Any]] = [
        {"step": 1, "action": "ingest_recommendations", "detail": f"Loaded {len(recs)} recommendations"},
        {"step": 2, "action": "select_formats", "detail": f"Generating {len(formats)} policy formats"},
    ]
    prev_ver = previous.version if previous else None
    policies = []
    for fmt in formats:
        if fmt not in ALL_FORMATS:
            continue
        policy = render_policy(
            fmt=fmt,
            tenant_id=bundle.tenant_id,
            agent_id=bundle.agent_id,
            version=bundle.policy_version,
            source=bundle.source,
            recs=recs,
            risk=bundle.risk or {},
            compliance=bundle.compliance or {},
            previous_version=prev_ver,
        )
        # auto-validate each artifact lightly
        policy.validation = validate_content(policy.content, fmt)
        policies.append(policy)
        reasoning.append(
            {
                "step": len(reasoning) + 1,
                "action": "generate_policy",
                "detail": f"{fmt.value} -> {policy.filename} ({policy.validation.status.value})",
            }
        )

    artifacts = [p.artifact for p in policies if p.artifact]
    named = {a.filename: a.content for a in artifacts}
    package_validation = ValidationResult(
        status=ValidationStatus.VALID
        if all(p.validation.status != ValidationStatus.INVALID for p in policies)
        else ValidationStatus.INVALID,
        checked_at=utcnow(),
        errors=[e for p in policies for e in p.validation.errors],
        warnings=[w for p in policies for w in p.validation.warnings],
        checks=[{"filename": p.filename, "status": p.validation.status.value} for p in policies],
    )
    summary = (
        f"Generated {len(policies)} deployment-ready policies for {bundle.agent_id} "
        f"(version={bundle.policy_version}, source={bundle.source})"
    )
    return PolicyPackage(
        tenant_id=bundle.tenant_id,
        agent_id=bundle.agent_id,
        agent_version=AGENT_VERSION,
        version=bundle.policy_version,
        source=bundle.source,
        policies=policies,
        artifacts=artifacts,
        named_artifacts=named,
        confidence=Confidence(score=0.9 if recs else 0.65, rationale="recommendation-driven generation"),
        reasoning_path=reasoning,
        summary=summary,
        validation=package_validation,
        rollback=RollbackPlan(
            strategy="replace_previous_version",
            previous_version=prev_ver,
            steps=[
                "Store current package_id as rollback checkpoint",
                "On failure, re-apply previous package artifacts",
                "Clear CDN/cache for policy endpoints",
                "Re-run POST /policy/validate",
            ],
            safe_to_auto_rollback=True,
        ),
    )


def validate_content(content: str, fmt: PolicyFormat | None = None) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []
    if not content or not content.strip():
        errors.append("Empty policy content")
    if fmt in {PolicyFormat.JSON, PolicyFormat.OPENAI_GUARDRAILS, PolicyFormat.AZURE_AI_FOUNDRY,
               PolicyFormat.LANGGRAPH, PolicyFormat.CREWAI, PolicyFormat.AUTOGEN,
               PolicyFormat.SEMANTIC_KERNEL, PolicyFormat.API_GATEWAY, PolicyFormat.PROMPT,
               PolicyFormat.IDENTITY, PolicyFormat.RUNTIME, PolicyFormat.DLP} or (
        fmt is None and content.lstrip().startswith("{")
    ):
        try:
            json.loads(content)
            checks.append({"check": "json_parse", "ok": True})
        except json.JSONDecodeError as exc:
            errors.append(f"JSON parse error: {exc}")
            checks.append({"check": "json_parse", "ok": False})
    if fmt in {PolicyFormat.YAML, PolicyFormat.KUBERNETES, PolicyFormat.ADMISSION_CONTROLLER} or (
        fmt is None and (content.lstrip().startswith("apiVersion") or ":" in content[:80])
    ):
        try:
            yaml.safe_load(content)
            checks.append({"check": "yaml_parse", "ok": True})
        except yaml.YAMLError as exc:
            errors.append(f"YAML parse error: {exc}")
            checks.append({"check": "yaml_parse", "ok": False})
    if fmt == PolicyFormat.OPA_REGO:
        if "package " not in content:
            errors.append("Rego missing package declaration")
        if "allow" not in content and "deny" not in content:
            warnings.append("Rego has no allow/deny rules")
        checks.append({"check": "rego_structure", "ok": "package " in content})
    if fmt == PolicyFormat.TERRAFORM:
        if "terraform" not in content and "resource" not in content:
            errors.append("Terraform content missing resource blocks")
        checks.append({"check": "terraform_structure", "ok": "resource" in content})
    status = ValidationStatus.INVALID if errors else (ValidationStatus.WARNING if warnings else ValidationStatus.VALID)
    return ValidationResult(status=status, checked_at=utcnow(), errors=errors, warnings=warnings, checks=checks)
