"""Tool definition and function-calling schema detection."""

from __future__ import annotations

import json
import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, iter_files, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

TOOL_PATTERNS = [
    re.compile(r"@tool\b"),
    re.compile(r"\bTool\s*\("),
    re.compile(r"function_calling"),
    re.compile(r'"type"\s*:\s*"function"'),
    re.compile(r"tools\s*=\s*\["),
]


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class ToolDetector(BaseDetector):
    detector_id = "tool.detector.v1"
    section = FindingSection.INTERFACES
    default_category = FindingCategory.TOOL

    async def detect(self, workspace_path: Path) -> list:
        findings = []

        for path in iter_files(workspace_path, extensions={".py", ".ts", ".js", ".json", ".yaml", ".yml"}):
            text = read_text(path)
            if not text:
                continue

            tool_names: list[str] = []
            for pattern in TOOL_PATTERNS:
                if pattern.search(text):
                    tool_names.extend(_extract_tool_names(text, path))

            if not tool_names and "tools" in path.name.lower():
                tool_names.append(path.stem)

            for name in dict.fromkeys(tool_names):
                findings.append(
                    self.finding(
                        name=name,
                        confidence=0.82,
                        rationale="Tool definition or function-calling schema",
                        path=str(path),
                    )
                )
        return findings


def _extract_tool_names(text: str, path: Path) -> list[str]:
    names: list[str] = []
    if path.suffix == ".py":
        for match in re.finditer(r"@tool(?:\s*\([^)]*\))?\s*\ndef\s+(\w+)", text):
            names.append(match.group(1))
        for match in re.finditer(r"def\s+(\w+)\s*\([^)]*\):[^\n]*tool", text, re.I):
            names.append(match.group(1))
    if path.suffix in {".json", ".yaml", ".yml"}:
        try:
            data = json.loads(text) if path.suffix == ".json" else None
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            tools = data.get("tools") or data.get("functions") or []
            if isinstance(tools, list):
                for item in tools:
                    if isinstance(item, dict):
                        fn = item.get("function") or item
                        if isinstance(fn, dict) and fn.get("name"):
                            names.append(str(fn["name"]))
    if not names:
        names.append("tool-schema")
    return names
