"""Package manager detection from manifest files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

MANIFESTS: dict[str, tuple[str, str | None]] = {
    "package.json": ("npm", None),
    "package-lock.json": ("npm", None),
    "pnpm-lock.yaml": ("pnpm", None),
    "yarn.lock": ("yarn", None),
    "pyproject.toml": ("poetry", None),
    "requirements.txt": ("pip", None),
    "Pipfile": ("pipenv", None),
    "poetry.lock": ("poetry", None),
    "go.mod": ("go-modules", None),
    "Cargo.toml": ("cargo", None),
    "pom.xml": ("maven", None),
    "build.gradle": ("gradle", None),
    "build.gradle.kts": ("gradle", None),
    "Gemfile": ("bundler", None),
    "composer.json": ("composer", None),
}


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class PackageManagerDetector(BaseDetector):
    detector_id = "package_manager.detector.v1"
    section = FindingSection.IDENTITY
    default_category = FindingCategory.PACKAGE_MANAGER

    async def detect(self, workspace_path: Path) -> list:
        findings = []
        for name, (manager, _) in MANIFESTS.items():
            for path in workspace_path.rglob(name):
                if not path.is_file() or any(
                    p.startswith(".")
                    for p in path.relative_to(workspace_path).parts[:-1]
                ):
                    continue
                version = _extract_version(path, manager)
                findings.append(
                    self.finding(
                        name=manager,
                        version=version,
                        confidence=0.92,
                        rationale=f"Found {name}",
                        path=str(path),
                    )
                )
        return findings


def _extract_version(path: Path, manager: str) -> str | None:
    text = read_text(path)
    if not text:
        return None
    if path.name == "package.json":
        try:
            data = json.loads(text)
            return str(data.get("packageManager", "").split("@")[-1]) or None
        except json.JSONDecodeError:
            return None
    if path.name == "pyproject.toml":
        match = re.search(r'poetry\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"', text)
        return match.group(1) if match else None
    if path.name == "go.mod":
        match = re.search(r"^go\s+(\S+)", text, re.MULTILINE)
        return match.group(1) if match else None
    return None
