"""Model name detection in env, config, and code."""

from __future__ import annotations

import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import (
    BaseDetector,
    iter_files,
    read_text,
)
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

MODEL_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\bgpt-4[o1.-]*[\w.-]*", re.I), "openai", 0.9),
    (re.compile(r"\bgpt-3\.5[\w.-]*", re.I), "openai", 0.85),
    (re.compile(r"\bclaude-[\w.-]+", re.I), "anthropic", 0.9),
    (re.compile(r"\bllama-[\w.-]+", re.I), "meta", 0.85),
    (re.compile(r"\bmistral-[\w.-]+", re.I), "mistral", 0.85),
    (re.compile(r"\bgemini-[\w.-]+", re.I), "google", 0.85),
    (
        re.compile(r"AZURE_OPENAI_DEPLOYMENT(?:_NAME)?[=:\s\"']+([\w-]+)", re.I),
        "azure-openai",
        0.92,
    ),
    (re.compile(r"deployment[_-]?name[=:\s\"']+([\w-]+)", re.I), "azure-openai", 0.8),
    (re.compile(r"\bo\d-mini\b", re.I), "openai", 0.88),
]


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class ModelDetector(BaseDetector):
    detector_id = "model.detector.v1"
    section = FindingSection.AI
    default_category = FindingCategory.MODEL

    async def detect(self, workspace_path: Path) -> list:
        seen: set[str] = set()
        findings = []

        text_extensions = {
            ".py",
            ".ts",
            ".js",
            ".json",
            ".yaml",
            ".yml",
            ".env",
            ".toml",
            ".md",
            ".txt",
        }
        globs = list(iter_files(workspace_path, extensions=text_extensions))
        globs.extend(p for p in workspace_path.rglob(".env*") if p.is_file())

        for path in globs:
            text = read_text(path)
            if not text:
                continue
            for pattern, provider, confidence in MODEL_PATTERNS:
                for match in pattern.finditer(text):
                    model_name = match.group(1) if match.lastindex else match.group(0)
                    key = model_name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    line = text[: match.start()].count("\n") + 1
                    findings.append(
                        self.finding(
                            name=model_name,
                            confidence=confidence,
                            rationale=f"Model reference ({provider})",
                            path=str(path),
                            line=line,
                            attributes={"provider": provider},
                        )
                    )
        return findings
