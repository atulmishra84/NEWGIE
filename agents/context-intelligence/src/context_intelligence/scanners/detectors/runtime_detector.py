"""Runtime detection from Dockerfiles and version pins."""

from __future__ import annotations

import json
import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, iter_files, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class RuntimeDetector(BaseDetector):
    detector_id = "runtime.detector.v1"
    section = FindingSection.IDENTITY
    default_category = FindingCategory.RUNTIME

    async def detect(self, workspace_path: Path) -> list:
        findings = []

        for dockerfile in iter_files(workspace_path, names={"Dockerfile", "Containerfile"}):
            text = read_text(dockerfile)
            if not text:
                continue
            for line in text.splitlines():
                if line.upper().startswith("FROM "):
                    image = line.split(maxsplit=1)[1].split()[0]
                    findings.append(
                        self.finding(
                            name="container",
                            version=image,
                            confidence=0.9,
                            rationale="Dockerfile base image",
                            path=str(dockerfile),
                            attributes={"base_image": image},
                        )
                    )
                    runtime = _runtime_from_image(image)
                    if runtime:
                        findings.append(
                            self.finding(
                                name=runtime[0],
                                version=runtime[1],
                                confidence=0.85,
                                rationale="Inferred from base image",
                                path=str(dockerfile),
                            )
                        )

        py_version = workspace_path / ".python-version"
        if py_version.is_file():
            findings.append(
                self.finding(
                    name="python",
                    version=py_version.read_text(encoding="utf-8").strip(),
                    confidence=0.95,
                    rationale="Found .python-version",
                    path=str(py_version),
                )
            )

        runtime_txt = workspace_path / "runtime.txt"
        if runtime_txt.is_file():
            findings.append(
                self.finding(
                    name="python",
                    version=runtime_txt.read_text(encoding="utf-8").strip(),
                    confidence=0.9,
                    rationale="Found runtime.txt",
                    path=str(runtime_txt),
                )
            )

        for pkg_json in workspace_path.rglob("package.json"):
            if not pkg_json.is_file():
                continue
            text = read_text(pkg_json)
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            engines = data.get("engines") or {}
            node = engines.get("node")
            if node:
                findings.append(
                    self.finding(
                        name="node",
                        version=str(node),
                        confidence=0.88,
                        rationale="package.json engines.node",
                        path=str(pkg_json),
                    )
                )
        return findings


def _runtime_from_image(image: str) -> tuple[str, str] | None:
    lowered = image.lower()
    patterns = [
        (r"python[:/]([\d.]+)", "python"),
        (r"node[:/]([\d.]+)", "node"),
        (r"golang[:/]([\d.]+)", "go"),
        (r"openjdk[:/]([\d.]+)", "java"),
        (r"rust[:/]([\d.]+)", "rust"),
    ]
    for pattern, name in patterns:
        match = re.search(pattern, lowered)
        if match:
            return name, match.group(1)
    return None
