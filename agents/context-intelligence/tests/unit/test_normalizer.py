"""Unit tests for detection normalizer."""

from __future__ import annotations

from context_intelligence.domain.normalizer import (
    merge_attributes,
    normalize_framework_hint,
    normalize_package_name,
    normalize_version,
    to_detected_item,
)


def test_normalize_package_name():
    assert normalize_package_name("LangGraph") == "langgraph"
    assert normalize_package_name("open_ai") == "open-ai"


def test_normalize_version():
    assert normalize_version("^0.2.0") == "0.2.0"
    assert normalize_version(None) is None


def test_normalize_framework_hint():
    assert normalize_framework_hint("langgraph") == "langgraph"
    assert normalize_framework_hint("OpenAI") == "openai"


def test_to_detected_item_includes_evidence():
    item = to_detected_item(
        "langgraph",
        version="0.2.0",
        detector_id="test.detector",
        path="pyproject.toml",
        line=5,
    )
    assert item.name == "langgraph"
    assert item.version == "0.2.0"
    assert len(item.evidence) == 1
    assert item.evidence[0].detector_id == "test.detector"


def test_merge_attributes():
    base = {"tags": ["a"], "meta": {"x": 1}}
    extra = {"tags": ["b"], "meta": {"y": 2}}
    merged = merge_attributes(base, extra)
    assert merged["tags"] == ["a", "b"]
    assert merged["meta"] == {"x": 1, "y": 2}
