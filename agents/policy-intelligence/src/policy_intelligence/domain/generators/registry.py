"""Generate deployment-ready artifacts for all supported targets/formats."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import yaml
from gie_contracts.policy import (
    GeneratedArtifact,
    GuardrailRecommendation,
    OutputFormat,
    PolicyInputBundle,
    PolicyTarget,
)

from policy_intelligence.domain.generators import (
    autogen as gen_autogen,
    azure_foundry as gen_azure,
    crewai as gen_crewai,
    langgraph as gen_langgraph,
    nemo as gen_nemo,
    openai as gen_openai,
    opa as gen_opa,
    presidio as gen_presidio,
)


_GENERATORS = {
    PolicyTarget.OPENAI: gen_openai.render,
    PolicyTarget.AZURE_AI_FOUNDRY: gen_azure.render,
    PolicyTarget.LANGGRAPH: gen_langgraph.render,
    PolicyTarget.CREWAI: gen_crewai.render,
    PolicyTarget.AUTOGEN: gen_autogen.render,
    PolicyTarget.OPA_REGO: gen_opa.render,
    PolicyTarget.NVIDIA_NEMO: gen_nemo.render,
    PolicyTarget.PRESIDIO: gen_presidio.render,
}


def generate_artifacts(
    recommendations: list[GuardrailRecommendation],
    bundle: PolicyInputBundle,
) -> list[GeneratedArtifact]:
    targets = bundle.targets or list(PolicyTarget)
    formats = bundle.formats or list(OutputFormat)
    artifacts: list[GeneratedArtifact] = []
    for target in targets:
        renderer = _GENERATORS[target]
        native = renderer(recommendations, bundle)
        produced = _materialize(target, native, formats)
        artifacts.extend(produced)
    return artifacts


def _materialize(target: PolicyTarget, native: dict[str, Any], formats: list[OutputFormat]) -> list[GeneratedArtifact]:
    out: list[GeneratedArtifact] = []
    # Always keep vendor-native structure
    if OutputFormat.VENDOR_NATIVE in formats or OutputFormat.JSON in formats:
        content = json.dumps(native, indent=2)
        fmt = OutputFormat.VENDOR_NATIVE if OutputFormat.VENDOR_NATIVE in formats else OutputFormat.JSON
        out.append(_art(target, fmt, f"{target.value}.policy.json", "application/json", content))
    if OutputFormat.YAML in formats:
        content = yaml.safe_dump(native, sort_keys=False)
        out.append(_art(target, OutputFormat.YAML, f"{target.value}.policy.yaml", "application/yaml", content))
    if OutputFormat.REGO in formats:
        # OPA target emits real rego; others emit wrapper package referencing controls
        if target == PolicyTarget.OPA_REGO:
            rego = native.get("rego", "")
        else:
            rego = _wrapper_rego(target, native)
        out.append(_art(target, OutputFormat.REGO, f"{target.value}.rego", "text/rego", rego))
    return out


def _wrapper_rego(target: PolicyTarget, native: dict[str, Any]) -> str:
    controls = native.get("controls", [])
    ids = [c.get("id", c) if isinstance(c, dict) else str(c) for c in controls]
    lines = [
        f"package gie.policy.{target.value.replace('-', '_')}",
        "",
        "import future.keywords.if",
        "",
        "default allow := false",
        "",
        "required_controls := {",
    ]
    for i in ids:
        lines.append(f'  "{i}",')
    lines += [
        "}",
        "",
        "allow if {",
        "  count(required_controls - {c | c := input.enabled_controls[_]}) == 0",
        "}",
        "",
    ]
    return chr(10).join(lines)


def _art(target: PolicyTarget, fmt: OutputFormat, filename: str, ctype: str, content: str) -> GeneratedArtifact:
    return GeneratedArtifact(
        target=target,
        format=fmt,
        filename=filename,
        content_type=ctype,
        content=content,
        checksum=hashlib.sha256(content.encode()).hexdigest(),
    )
