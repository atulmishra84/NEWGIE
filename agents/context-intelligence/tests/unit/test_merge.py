"""Unit tests for context model merge."""

from __future__ import annotations

from uuid import uuid4

from gie_contracts.context_model import (
    Confidence,
    ContextModel,
    ProvenanceSection,
    SecretFinding,
    Severity,
)

from context_intelligence.domain.merge import merge_context_models
from context_intelligence.domain.normalizer import to_detected_item


def _base_model() -> ContextModel:
    return ContextModel(
        provenance=ProvenanceSection(
            agent_version="1.0.0",
            scan_id=uuid4(),
            tenant_id="test",
            source_type="folder",
            detectors=["a"],
            confidence=Confidence(score=0.5),
        )
    )


def test_merge_deduplicates_frameworks():
    base = _base_model()
    base.ai.frameworks.append(
        to_detected_item("langgraph", version="0.1", detector_id="a", confidence=0.6)
    )
    other = _base_model()
    other.ai.frameworks.append(
        to_detected_item("langgraph", version="0.1", detector_id="b", confidence=0.9)
    )
    merged = merge_context_models(base, other)
    assert len(merged.ai.frameworks) == 1
    assert merged.ai.frameworks[0].confidence.score == 0.9


def test_merge_combines_detectors():
    base = _base_model()
    other = _base_model()
    other.provenance.detectors = ["manifest.detector.v1"]
    merged = merge_context_models(base, other)
    assert "a" in merged.provenance.detectors
    assert "manifest.detector.v1" in merged.provenance.detectors


def test_merge_deduplicates_secrets():
    base = _base_model()
    base.data.secret_findings.append(
        SecretFinding(
            kind="openai_api_key",
            location=".env",
            fingerprint="sha256:abc",
            severity=Severity.CRITICAL,
        )
    )
    other = _base_model()
    other.data.secret_findings.append(
        SecretFinding(
            kind="openai_api_key",
            location=".env",
            fingerprint="sha256:abc",
            severity=Severity.CRITICAL,
        )
    )
    merged = merge_context_models(base, other)
    assert len(merged.data.secret_findings) == 1
