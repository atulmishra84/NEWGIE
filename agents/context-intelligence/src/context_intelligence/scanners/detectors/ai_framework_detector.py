"""AI framework detection from imports, deps, and config."""

from __future__ import annotations

import json
import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import (
    BaseDetector,
    iter_files,
    read_text,
)
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

FRAMEWORKS: list[tuple[str, list[str], list[str], float]] = [
    ("langgraph", ["langgraph"], ["langgraph", "StateGraph"], 0.9),
    (
        "openai-agents",
        ["openai-agents", "agents"],
        ["from agents", "import agents"],
        0.88,
    ),
    ("crewai", ["crewai"], ["from crewai", "import crewai", "Crew("], 0.9),
    (
        "autogen",
        ["pyautogen", "autogen"],
        ["import autogen", "AutoGen", "AssistantAgent"],
        0.88,
    ),
    (
        "semantic-kernel",
        ["semantic-kernel"],
        ["semantic_kernel", "SemanticKernel"],
        0.9,
    ),
    (
        "azure-ai-foundry",
        ["azure-ai-projects", "azure-ai-inference"],
        ["azure.ai", "AIFoundry", "azure_ai"],
        0.85,
    ),
    (
        "langchain",
        ["langchain", "langchain-core"],
        ["from langchain", "import langchain"],
        0.85,
    ),
    ("llamaindex", ["llama-index"], ["llama_index", "LlamaIndex"], 0.85),
]


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class AiFrameworkDetector(BaseDetector):
    detector_id = "ai_framework.detector.v1"
    section = FindingSection.AI
    default_category = FindingCategory.FRAMEWORK

    async def detect(self, workspace_path: Path) -> list:
        findings = []
        dep_index = _build_dependency_index(workspace_path)

        for name, packages, needles, confidence in FRAMEWORKS:
            version = _first_version(dep_index, packages)
            evidence_path = None
            if version:
                findings.append(
                    self.finding(
                        name=name,
                        version=version,
                        confidence=confidence,
                        rationale="Declared in dependencies",
                        attributes={"packages": packages},
                    )
                )
                continue

            for path in iter_files(
                workspace_path,
                extensions={".py", ".ts", ".js", ".ipynb", ".yaml", ".yml"},
            ):
                text = read_text(path)
                if not text:
                    continue
                if any(needle.lower() in text.lower() for needle in needles):
                    evidence_path = str(path)
                    findings.append(
                        self.finding(
                            name=name,
                            confidence=confidence - 0.05,
                            rationale="Import or API usage detected",
                            path=evidence_path,
                        )
                    )
                    break
        return findings


def _build_dependency_index(root: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in root.rglob("pyproject.toml"):
        text = read_text(path)
        if text:
            for match in re.finditer(r'"([^"]+)"\s*=\s*"([^"]+)"', text):
                index[match.group(1).lower()] = match.group(2)
    for path in root.rglob("requirements*.txt"):
        text = read_text(path)
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(
                r"^([A-Za-z0-9_.-]+)(?:\[.*\])?(?:([=<>~!]+)([\d.]+))?", line
            )
            if match:
                index[match.group(1).lower()] = match.group(3) or "*"
    for path in root.rglob("package.json"):
        text = read_text(path)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        for section in ("dependencies", "devDependencies"):
            for pkg, ver in (data.get(section) or {}).items():
                index[pkg.lower()] = str(ver).lstrip("^~")
    return index


def _first_version(index: dict[str, str], packages: list[str]) -> str | None:
    for pkg in packages:
        if pkg.lower() in index:
            return index[pkg.lower()]
    return None
