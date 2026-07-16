"""Prompt file and system prompt heuristics."""

from __future__ import annotations

import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, iter_files, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

PROMPT_DIR_NAMES = {"prompts", "prompt", "templates", "system_prompts"}
SYSTEM_PROMPT_RE = re.compile(
    r"(system[_\s-]?prompt|SYSTEM_PROMPT|role\s*:\s*['\"]system['\"])",
    re.IGNORECASE,
)


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class PromptDetector(BaseDetector):
    detector_id = "prompt.detector.v1"
    section = FindingSection.AI
    default_category = FindingCategory.PROMPT

    async def detect(self, workspace_path: Path) -> list:
        findings = []

        for path in workspace_path.rglob("*"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(workspace_path).parts
            if path.suffix == ".prompt" or (
                len(rel_parts) >= 2 and rel_parts[0].lower() in PROMPT_DIR_NAMES
            ):
                findings.append(
                    self.finding(
                        name=path.stem,
                        confidence=0.9,
                        rationale="Prompt file or prompts/ directory",
                        path=str(path),
                        attributes={"kind": "file"},
                    )
                )

        for path in iter_files(workspace_path, extensions={".py", ".ts", ".js", ".yaml", ".json", ".md"}):
            text = read_text(path)
            if not text or not SYSTEM_PROMPT_RE.search(text):
                continue
            findings.append(
                self.finding(
                    name="system-prompt",
                    confidence=0.75,
                    rationale="System prompt string heuristic",
                    path=str(path),
                    attributes={"kind": "inline"},
                )
            )
        return findings
