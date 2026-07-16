"""Chaos tests — detector failure isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from context_intelligence.domain.findings import DetectionFinding, FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector
from context_intelligence.scanners.registry import DetectorRegistry


class FailingDetector(BaseDetector):
    detector_id = "failing.detector.v1"
    section = FindingSection.DATA
    default_category = FindingCategory.SECRET

    async def detect(self, workspace_path: Path) -> list[DetectionFinding]:
        raise RuntimeError("simulated detector failure")


class WorkingDetector(BaseDetector):
    detector_id = "working.detector.v1"
    section = FindingSection.AI
    default_category = FindingCategory.FRAMEWORK

    async def detect(self, workspace_path: Path) -> list[DetectionFinding]:
        return [
            self.finding(
                name="langgraph",
                confidence=0.9,
                rationale="test finding",
                path="pyproject.toml",
            )
        ]


@pytest.mark.asyncio
async def test_failing_detector_does_not_abort_registry(tmp_path: Path):
    registry = DetectorRegistry()
    registry.register(FailingDetector)
    registry.register(WorkingDetector)
    findings = await registry.run_all(tmp_path)
    error_findings = [f for f in findings if f.name == "detector_error"]
    success_findings = [f for f in findings if f.name == "langgraph"]
    assert len(error_findings) == 1
    assert error_findings[0].detector_id == "failing.detector.v1"
    assert len(success_findings) == 1
