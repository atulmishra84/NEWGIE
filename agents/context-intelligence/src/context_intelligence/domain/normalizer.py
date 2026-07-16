"""Normalize raw detector output into Context Model sections."""

from __future__ import annotations

from typing import Any

from gie_contracts.context_model import Confidence, DetectedItem, EvidenceRef


def normalize_package_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def normalize_version(version: str | None) -> str | None:
    if version is None:
        return None
    cleaned = version.strip().lstrip("^~>=<")
    return cleaned or None


def to_detected_item(
    name: str,
    *,
    version: str | None = None,
    confidence: float = 0.8,
    detector_id: str,
    path: str | None = None,
    line: int | None = None,
    attributes: dict[str, Any] | None = None,
) -> DetectedItem:
    evidence: list[EvidenceRef] = []
    if path:
        evidence.append(
            EvidenceRef(
                evidence_id=f"{detector_id}:{path}:{line or 0}",
                path=path,
                start_line=line,
                end_line=line,
                detector_id=detector_id,
            )
        )
    return DetectedItem(
        name=normalize_package_name(name),
        version=normalize_version(version),
        confidence=Confidence(score=confidence),
        evidence=evidence,
        attributes=attributes or {},
    )


def normalize_framework_hint(raw: str) -> str:
    aliases = {
        "langgraph": "langgraph",
        "lang-chain": "langchain",
        "openai": "openai",
        "openai-agents": "openai-agents",
        "crewai": "crewai",
        "autogen": "autogen",
        "semantic-kernel": "semantic-kernel",
    }
    key = raw.strip().lower()
    return aliases.get(key, key)


def merge_attributes(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for k, v in extra.items():
        if k not in merged:
            merged[k] = v
        elif isinstance(merged[k], list) and isinstance(v, list):
            merged[k] = list(dict.fromkeys([*merged[k], *v]))
        elif isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = merge_attributes(merged[k], v)
    return merged
