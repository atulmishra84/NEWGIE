"""API framework and OpenAPI detection."""

from __future__ import annotations

import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, iter_files, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

API_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("fastapi", re.compile(r"\b(FastAPI|APIRouter|@app\.(get|post|put|delete))", re.I), 0.9),
    ("flask", re.compile(r"\b(Flask|@app\.route|Blueprint)", re.I), 0.88),
    ("express", re.compile(r"\b(express\(\)|app\.(get|post|put|delete)\()", re.I), 0.88),
    ("django-rest", re.compile(r"\brest_framework\b", re.I), 0.85),
    ("openapi", re.compile(r"\bopenapi:\s*['\"]?3", re.I), 0.95),
]


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class ApiDetector(BaseDetector):
    detector_id = "api.detector.v1"
    section = FindingSection.INTERFACES
    default_category = FindingCategory.API

    async def detect(self, workspace_path: Path) -> list:
        findings = []

        for spec_name in ("openapi.yaml", "openapi.yml", "swagger.yaml", "swagger.json"):
            for path in workspace_path.rglob(spec_name):
                if path.is_file():
                    findings.append(
                        self.finding(
                            name="openapi",
                            confidence=0.98,
                            rationale=f"Found {spec_name}",
                            path=str(path),
                            attributes={"spec_file": spec_name},
                        )
                    )

        for path in iter_files(workspace_path, extensions={".py", ".js", ".ts"}):
            text = read_text(path)
            if not text:
                continue
            for name, pattern, confidence in API_PATTERNS:
                if pattern.search(text):
                    findings.append(
                        self.finding(
                            name=name,
                            confidence=confidence,
                            rationale="Route or framework usage",
                            path=str(path),
                        )
                    )
        return findings
