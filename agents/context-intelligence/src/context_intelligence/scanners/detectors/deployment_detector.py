"""Deployment artifact detection."""

from __future__ import annotations

import re
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class DeploymentDetector(BaseDetector):
    detector_id = "deployment.detector.v1"
    section = FindingSection.DEPLOYMENT
    default_category = FindingCategory.KUBERNETES

    async def detect(self, workspace_path: Path) -> list:
        findings = []

        for path in workspace_path.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            rel = path.relative_to(workspace_path).as_posix()

            if name in {
                "docker-compose.yml",
                "docker-compose.yaml",
                "compose.yaml",
                "compose.yml",
            }:
                findings.append(
                    self.finding(
                        category=FindingCategory.CONTAINER,
                        name="docker-compose",
                        confidence=0.95,
                        rationale="Docker Compose file",
                        path=str(path),
                    )
                )

            if path.suffix in {".yaml", ".yml"} and _looks_like_k8s(
                path, read_text(path)
            ):
                findings.append(
                    self.finding(
                        category=FindingCategory.KUBERNETES,
                        name="kubernetes-manifest",
                        confidence=0.9,
                        rationale="Kubernetes YAML manifest",
                        path=str(path),
                    )
                )

            if name.startswith("chart.yaml") or "/charts/" in rel:
                findings.append(
                    self.finding(
                        category=FindingCategory.KUBERNETES,
                        name="helm",
                        confidence=0.88,
                        rationale="Helm chart detected",
                        path=str(path),
                    )
                )

            if path.suffix == ".tf" or name == "terraform.tfvars":
                findings.append(
                    self.finding(
                        category=FindingCategory.CLOUD_RESOURCE,
                        name="terraform",
                        confidence=0.9,
                        rationale="Terraform configuration",
                        path=str(path),
                    )
                )

            if name == "dockerfile" or name.startswith("dockerfile."):
                findings.append(
                    self.finding(
                        category=FindingCategory.CONTAINER,
                        name="dockerfile",
                        confidence=0.95,
                        rationale="Dockerfile present",
                        path=str(path),
                    )
                )
        return findings


def _looks_like_k8s(path: Path, text: str | None) -> bool:
    if not text:
        return False
    if re.search(r"^apiVersion:\s*", text, re.MULTILINE) and re.search(
        r"^kind:\s*", text, re.MULTILINE
    ):
        return True
    return "kubernetes" in path.as_posix().lower()
