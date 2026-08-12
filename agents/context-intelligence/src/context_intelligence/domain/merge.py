"""Merge partial Context Models from multiple detectors."""

from __future__ import annotations

from gie_contracts.context_model import ContextModel, DetectedItem, SecretFinding


def _dedupe_items(items: list[DetectedItem]) -> list[DetectedItem]:
    seen: dict[str, DetectedItem] = {}
    for item in items:
        key = f"{item.name}:{item.version or ''}"
        existing = seen.get(key)
        if existing is None or item.confidence.score > existing.confidence.score:
            seen[key] = item
    return list(seen.values())


def _dedupe_secrets(findings: list[SecretFinding]) -> list[SecretFinding]:
    seen: dict[str, SecretFinding] = {}
    for finding in findings:
        key = f"{finding.kind}:{finding.location}:{finding.fingerprint}"
        if key not in seen:
            seen[key] = finding
    return list(seen.values())


def merge_context_models(base: ContextModel, *others: ContextModel) -> ContextModel:
    """Merge detector outputs; later models enrich earlier ones."""
    merged = base.model_copy(deep=True)
    for other in others:
        merged.identity.languages = _dedupe_items(
            [*merged.identity.languages, *other.identity.languages]
        )
        merged.identity.package_managers = _dedupe_items(
            [*merged.identity.package_managers, *other.identity.package_managers]
        )
        merged.identity.runtimes = _dedupe_items(
            [*merged.identity.runtimes, *other.identity.runtimes]
        )
        merged.ai.frameworks = _dedupe_items(
            [*merged.ai.frameworks, *other.ai.frameworks]
        )
        merged.ai.sdks = _dedupe_items([*merged.ai.sdks, *other.ai.sdks])
        merged.ai.models = _dedupe_items([*merged.ai.models, *other.ai.models])
        merged.ai.prompts = _dedupe_items([*merged.ai.prompts, *other.ai.prompts])
        merged.interfaces.mcp_servers = _dedupe_items(
            [*merged.interfaces.mcp_servers, *other.interfaces.mcp_servers]
        )
        merged.interfaces.tools = _dedupe_items(
            [*merged.interfaces.tools, *other.interfaces.tools]
        )
        merged.data.secret_findings = _dedupe_secrets(
            [*merged.data.secret_findings, *other.data.secret_findings]
        )
        merged.provenance.detectors = list(
            dict.fromkeys([*merged.provenance.detectors, *other.provenance.detectors])
        )
        merged.provenance.evidence.extend(other.provenance.evidence)
        merged.provenance.reasoning_path.extend(other.provenance.reasoning_path)
        if other.provenance.confidence.score > merged.provenance.confidence.score:
            merged.provenance.confidence = other.provenance.confidence
    return merged
