"""Render deployment-ready policies for every supported format."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import yaml

from gie_contracts.policy_generator import (
    ComplianceMapping,
    GeneratedPolicy,
    GeneratedPolicyArtifact,
    PolicyFormat,
    PolicyMetadata,
    RiskMapping,
    RollbackPlan,
    ValidationResult,
    ValidationStatus,
)

ALL_FORMATS = list(PolicyFormat)

FILENAME = {
    PolicyFormat.OPENAI_GUARDRAILS: "openai-policy.json",
    PolicyFormat.AZURE_AI_FOUNDRY: "azure-foundry-policy.json",
    PolicyFormat.LANGGRAPH: "langgraph-policy.json",
    PolicyFormat.CREWAI: "crewai-policy.json",
    PolicyFormat.AUTOGEN: "autogen-policy.json",
    PolicyFormat.SEMANTIC_KERNEL: "semantic-kernel-policy.json",
    PolicyFormat.NVIDIA_NEMO: "nemo-rails.co",
    PolicyFormat.OPA_REGO: "opa.rego",
    PolicyFormat.YAML: "guardrails.yaml",
    PolicyFormat.JSON: "guardrails.json",
    PolicyFormat.TERRAFORM: "guardrails.tf",
    PolicyFormat.KUBERNETES: "k8s-network-policy.yaml",
    PolicyFormat.ADMISSION_CONTROLLER: "validating-admission-policy.yaml",
    PolicyFormat.API_GATEWAY: "api-gateway-policy.json",
    PolicyFormat.PROMPT: "prompt-policy.json",
    PolicyFormat.IDENTITY: "identity-policy.json",
    PolicyFormat.RUNTIME: "runtime-policy.json",
    PolicyFormat.DLP: "dlp-policy.json",
}

CONTENT_TYPE = {
    PolicyFormat.OPA_REGO: "text/plain",
    PolicyFormat.NVIDIA_NEMO: "text/plain",
    PolicyFormat.TERRAFORM: "text/plain",
    PolicyFormat.YAML: "application/yaml",
    PolicyFormat.KUBERNETES: "application/yaml",
    PolicyFormat.ADMISSION_CONTROLLER: "application/yaml",
}


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _controls(recs: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for r in recs:
        out.extend(r.get("related_guardrails") or [])
        out.append(r.get("recommendation_id") or r.get("title") or "rec")
    return sorted({x for x in out if x})[:40]


def _risk_cats(recs: list[dict[str, Any]], risk: dict[str, Any]) -> list[str]:
    cats: list[str] = []
    for r in recs:
        if r.get("category"):
            cats.append(str(r["category"]))
    for f in (risk.get("factors") or [])[:10]:
        if isinstance(f, dict) and f.get("category"):
            cats.append(str(f["category"]))
    return sorted(set(cats))


def _comp_frameworks(
    compliance: dict[str, Any], recs: list[dict[str, Any]]
) -> list[str]:
    fws: list[str] = []
    for a in compliance.get("applicable_frameworks") or []:
        if isinstance(a, dict):
            fws.append(str(a.get("framework") or a.get("id") or ""))
        else:
            fws.append(str(a))
    for g in compliance.get("gaps") or []:
        if isinstance(g, dict) and g.get("framework"):
            fws.append(str(g["framework"]))
    for r in recs:
        for ref in r.get("knowledge_refs") or []:
            low = str(ref).lower()
            if any(
                k in low
                for k in ("hipaa", "gdpr", "soc2", "euai", "nist", "pci", "iso")
            ):
                fws.append(str(ref))
    return sorted({x for x in fws if x})[:20]


def _base_body(
    agent_id: str, version: str, controls: list[str], recs: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "version": version,
        "controls": controls,
        "recommendations": [
            {
                "id": r.get("recommendation_id"),
                "title": r.get("title"),
                "priority": r.get("priority"),
                "category": r.get("category"),
                "guardrails": r.get("related_guardrails") or [],
            }
            for r in recs
        ],
        "rules": {
            "block_prompt_injection": any("prompt" in str(r).lower() for r in recs)
            or "gr-prompt-firewall" in controls,
            "redact_pii": any(
                x in controls for x in ("gr-pii-presidio", "gr-output-filter")
            )
            or any("privacy" in str(r.get("category", "")).lower() for r in recs),
            "tool_allowlist": any("tool" in str(r).lower() for r in recs)
            or "gr-tool-allowlist" in controls,
            "require_human_approval": any(
                "human" in str(r).lower() or "autonomy" in str(r).lower() for r in recs
            ),
            "rate_limit": "gr-rate-limit" in controls
            or any("rate" in str(r).lower() for r in recs),
            "identity_rbac": "gr-identity-rbac" in controls
            or any("identity" in str(r.get("category", "")).lower() for r in recs),
        },
    }


def _dump_json(body: dict[str, Any]) -> str:
    return json.dumps(body, indent=2)


def _dump_yaml(body: dict[str, Any]) -> str:
    return yaml.safe_dump(body, sort_keys=False)


def _vendor_body(
    fmt: PolicyFormat, body: dict[str, Any], agent_id: str
) -> dict[str, Any]:
    rules = body.get("rules") or {}
    controls = body.get("controls") or []
    if fmt == PolicyFormat.OPENAI_GUARDRAILS:
        return {
            "object": "guardrails.policy",
            "name": agent_id,
            "version": body.get("version"),
            "steps": [
                {
                    "type": "input_filters",
                    "filters": ["jailbreak", "pii"]
                    if rules.get("block_prompt_injection")
                    else ["pii"],
                },
                {
                    "type": "output_filters",
                    "filters": ["pii", "toxic"]
                    if rules.get("redact_pii")
                    else ["toxic"],
                },
                {
                    "type": "tool_restrictions",
                    "mode": "allowlist" if rules.get("tool_allowlist") else "monitor",
                },
            ],
            "controls": controls,
        }
    if fmt == PolicyFormat.AZURE_AI_FOUNDRY:
        return {
            "schema": "azure.ai.foundry.policy/v1",
            "name": agent_id,
            "contentFilters": {
                "hate": "high",
                "self_harm": "high",
                "sexual": "high",
                "violence": "high",
                "prompt_shields": rules.get("block_prompt_injection", True),
            },
            "groundedness": True,
            "pii": rules.get("redact_pii", True),
            "controls": controls,
        }
    if fmt == PolicyFormat.LANGGRAPH:
        return {
            "framework": "langgraph",
            "middleware": ["PromptFirewall", "OutputFilter", "ToolGate"],
            "config": body,
        }
    if fmt == PolicyFormat.CREWAI:
        return {
            "framework": "crewai",
            "process_guards": rules,
            "tools_policy": "allowlist" if rules.get("tool_allowlist") else "open",
            "controls": controls,
        }
    if fmt == PolicyFormat.AUTOGEN:
        return {
            "framework": "autogen",
            "agent_constraints": rules,
            "human_input_mode": "ALWAYS"
            if rules.get("require_human_approval")
            else "NEVER",
            "controls": controls,
        }
    if fmt == PolicyFormat.SEMANTIC_KERNEL:
        return {
            "framework": "semantic_kernel",
            "filters": [
                "PromptInjectionFilter",
                "PiiRedactionFilter",
                "FunctionInvocationFilter",
            ],
            "settings": rules,
            "controls": controls,
        }
    if fmt == PolicyFormat.API_GATEWAY:
        return {
            "type": "api_gateway_policy",
            "rate_limit": {"enabled": rules.get("rate_limit", True), "rpm": 60},
            "auth": {"required": rules.get("identity_rbac", True)},
            "waf": {"prompt_injection": rules.get("block_prompt_injection", True)},
            "controls": controls,
        }
    if fmt == PolicyFormat.PROMPT:
        return {
            "type": "prompt_policy",
            "system_preamble": "Follow enterprise safety and privacy policies.",
            "deny_patterns": ["ignore previous instructions", "exfiltrate secrets"],
            "injection_threshold": 0.7,
            "controls": controls,
        }
    if fmt == PolicyFormat.IDENTITY:
        return {
            "type": "identity_policy",
            "require_mfa": True,
            "rbac": {
                "roles": ["viewer", "operator", "admin"],
                "tool_scopes": "least_privilege",
            },
            "controls": controls,
        }
    if fmt == PolicyFormat.RUNTIME:
        return {
            "type": "runtime_policy",
            "opa_package": "gie.guardrails",
            "enforce": True,
            "human_approval": rules.get("require_human_approval", False),
            "controls": controls,
        }
    if fmt == PolicyFormat.DLP:
        return {
            "type": "dlp_policy",
            "engine": "presidio",
            "entities": [
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "US_SSN",
                "CREDIT_CARD",
                "MEDICAL",
            ],
            "action": "redact",
            "controls": controls,
        }
    if fmt == PolicyFormat.JSON:
        return {
            "apiVersion": "gie.ai/v1",
            "kind": "GuardrailsPolicy",
            "metadata": {"name": agent_id, "version": body.get("version")},
            "spec": body,
        }
    if fmt == PolicyFormat.YAML:
        return {
            "apiVersion": "gie.ai/v1",
            "kind": "GuardrailsPolicy",
            "metadata": {"name": agent_id, "version": body.get("version")},
            "spec": body,
        }
    return body


def _render_content(
    fmt: PolicyFormat, body: dict[str, Any], agent_id: str
) -> tuple[dict[str, Any], str]:
    controls = body.get("controls") or []
    rules = body.get("rules") or {}

    if fmt == PolicyFormat.OPA_REGO:
        content = f"""package gie.guardrails

default allow = false

# Agent: {agent_id}
# Controls: {", ".join(controls[:12])}

allow {{
  input.action == "invoke"
  not deny
}}

deny {{
  input.prompt_injection_score > 0.7
}}

deny {{
  input.contains_pii
  {str(bool(rules.get("redact_pii"))).lower()}
}}

deny {{
  input.tool_name
  not input.tool_name in data.gie.allowed_tools
  {str(bool(rules.get("tool_allowlist"))).lower()}
}}

deny {{
  input.requires_approval
  not input.human_approved
}}
"""
        return {"raw": True, "controls": controls, "rules": rules}, content

    if fmt == PolicyFormat.NVIDIA_NEMO:
        content = f"""define user greeting
  "hello"

define bot inform
  "I follow enterprise guardrails for {agent_id}."

define flow guardrails
  user ...
  if $pii
    bot inform "I cannot share sensitive data."
  else
    bot respond
"""
        return {"raw": True, "controls": controls}, content

    if fmt == PolicyFormat.TERRAFORM:
        content = f"""# GIE Guardrails Terraform module for {agent_id}
terraform {{
  required_version = ">= 1.5.0"
}}

variable "agent_id" {{
  type    = string
  default = "{agent_id}"
}}

resource "local_file" "guardrails_policy" {{
  filename = "${{path.module}}/generated/guardrails.json"
  content  = jsonencode({{
    agent_id = var.agent_id
    version  = "{body.get("version", "1.0.0")}"
    controls = {json.dumps(controls)}
    rules    = {json.dumps(rules)}
  }})
}}

output "policy_path" {{
  value = local_file.guardrails_policy.filename
}}
"""
        return {"raw": True, "controls": controls, "rules": rules}, content

    if fmt == PolicyFormat.KUBERNETES:
        doc = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": f"gie-{agent_id}"[:63],
                "labels": {"app.kubernetes.io/managed-by": "gie-policy-generator"},
            },
            "spec": {
                "podSelector": {"matchLabels": {"gie.agent_id": agent_id}},
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [
                    {
                        "from": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {"gie.trust": "internal"}
                                }
                            }
                        ]
                    }
                ],
                "egress": [
                    {
                        "to": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {"gie.egress": "allowed"}
                                }
                            }
                        ]
                    }
                ],
            },
        }
        return doc, _dump_yaml(doc)

    if fmt == PolicyFormat.ADMISSION_CONTROLLER:
        doc = {
            "apiVersion": "admissionregistration.k8s.io/v1",
            "kind": "ValidatingAdmissionPolicy",
            "metadata": {"name": f"gie-ai-guardrails-{agent_id}"[:63]},
            "spec": {
                "failurePolicy": "Fail",
                "matchConstraints": {
                    "resourceRules": [
                        {
                            "apiGroups": ["apps"],
                            "apiVersions": ["v1"],
                            "operations": ["CREATE", "UPDATE"],
                            "resources": ["deployments"],
                        }
                    ]
                },
                "validations": [
                    {
                        "expression": "object.metadata.labels['gie.guardrails'] == 'enabled'",
                        "message": "gie.guardrails=enabled label required",
                    }
                ],
            },
        }
        return doc, _dump_yaml(doc)

    vendor = _vendor_body(fmt, body, agent_id)
    if fmt == PolicyFormat.YAML:
        return vendor, _dump_yaml(vendor)
    return vendor, _dump_json(vendor)


def render_policy(
    *,
    fmt: PolicyFormat,
    tenant_id: str,
    agent_id: str,
    version: str,
    source: str,
    recs: list[dict[str, Any]],
    risk: dict[str, Any],
    compliance: dict[str, Any],
    previous_version: str | None = None,
) -> GeneratedPolicy:
    controls = _controls(recs)
    body = _base_body(agent_id, version, controls, recs)
    rendered_body, content = _render_content(fmt, body, agent_id)
    filename = FILENAME[fmt]
    ctype = CONTENT_TYPE.get(fmt, "application/json")
    meta = PolicyMetadata(
        name=f"{fmt.value}-{agent_id}",
        description=f"Deployment-ready {fmt.value} policy generated from recommendations",
        version=version,
        source=source,
        tenant_id=tenant_id,
        agent_id=agent_id,
        tags=[fmt.value, "gie", "generated"],
    )
    artifact = GeneratedPolicyArtifact(
        filename=filename,
        format=fmt,
        content_type=ctype,
        content=content,
        checksum=_checksum(content),
    )
    return GeneratedPolicy(
        metadata=meta,
        format=fmt,
        body=rendered_body,
        content=content,
        filename=filename,
        content_type=ctype,
        compliance_mapping=ComplianceMapping(
            frameworks=_comp_frameworks(compliance, recs),
            controls=controls,
            notes="Mapped from compliance gaps and recommendation knowledge refs",
        ),
        risk_mapping=RiskMapping(
            categories=_risk_cats(recs, risk),
            severities=sorted(
                {str(r.get("priority")) for r in recs if r.get("priority")}
            ),
            recommendation_ids=[
                str(r.get("recommendation_id"))
                for r in recs
                if r.get("recommendation_id")
            ],
            risk_reduction=max(
                (float(r.get("risk_reduction") or 0) for r in recs), default=0.0
            )
            or None,
        ),
        validation=ValidationResult(status=ValidationStatus.PENDING),
        rollback=RollbackPlan(
            strategy="replace_previous_version",
            previous_version=previous_version,
            steps=[
                f"Retain prior artifact checksum for {filename}",
                f"Redeploy previous version {previous_version or 'N/A'} via GitOps/rollback API",
                "Invalidate runtime policy cache",
                "Verify health probes and deny-test suite",
            ],
            safe_to_auto_rollback=True,
        ),
        artifact=artifact,
    )
