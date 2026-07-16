"""Filesystem and manifest detectors."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from gie_contracts.context_model import ContextModel, ProvenanceSection

from context_intelligence.config import settings
from context_intelligence.domain.detectors.base import Detector, DetectorResult
from context_intelligence.domain.normalizer import to_detected_item
from context_intelligence.domain.secrets_detector import scan_file_for_secrets

AI_PACKAGE_HINTS = {
    "langgraph": ("langgraph", "ai.frameworks"),
    "langchain": ("langchain", "ai.frameworks"),
    "openai": ("openai", "ai.sdks"),
    "crewai": ("crewai", "ai.frameworks"),
    "autogen": ("autogen", "ai.frameworks"),
    "semantic-kernel": ("semantic-kernel", "ai.frameworks"),
}


class ManifestDetector(Detector):
    detector_id = "manifest.detector.v1"

    def detect(self, root: Path, *, tenant_id: str, scan_id: str) -> DetectorResult:
        model = ContextModel(
            provenance=ProvenanceSection(
                agent_version=settings.agent_version,
                scan_id=UUID(scan_id),
                tenant_id=tenant_id,
                source_type="folder",
                detectors=[self.detector_id],
            )
        )
        self._scan_package_json(root, model)
        self._scan_pyproject(root, model)
        self._scan_mcp_json(root, model)
        self._scan_prompts(root, model)
        self._scan_env_files(root, model)
        return DetectorResult(partial=model, detector_id=self.detector_id)

    def _scan_package_json(self, root: Path, model: ContextModel) -> None:
        path = root / "package.json"
        if not path.is_file():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for pkg, version in deps.items():
            hint = AI_PACKAGE_HINTS.get(pkg.lower())
            if hint:
                item = to_detected_item(
                    hint[0], version=str(version), detector_id=self.detector_id, path=str(path)
                )
                if hint[1] == "ai.frameworks":
                    model.ai.frameworks.append(item)
                else:
                    model.ai.sdks.append(item)
        model.identity.package_managers.append(
            to_detected_item("npm", detector_id=self.detector_id, path=str(path))
        )

    def _scan_pyproject(self, root: Path, model: ContextModel) -> None:
        path = root / "pyproject.toml"
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        model.identity.package_managers.append(
            to_detected_item("uv", detector_id=self.detector_id, path=str(path))
        )
        for pkg, (name, section) in AI_PACKAGE_HINTS.items():
            if pkg in text.lower():
                item = to_detected_item(name, detector_id=self.detector_id, path=str(path))
                if section == "ai.frameworks":
                    model.ai.frameworks.append(item)
                else:
                    model.ai.sdks.append(item)

    def _scan_mcp_json(self, root: Path, model: ContextModel) -> None:
        for candidate in (root / "mcp.json", root / ".cursor" / "mcp.json"):
            if not candidate.is_file():
                continue
            data = json.loads(candidate.read_text(encoding="utf-8"))
            servers = data.get("mcpServers") or data.get("servers") or {}
            for name in servers:
                model.interfaces.mcp_servers.append(
                    to_detected_item(name, detector_id=self.detector_id, path=str(candidate))
                )

    def _scan_prompts(self, root: Path, model: ContextModel) -> None:
        for path in root.rglob("*.prompt"):
            if path.is_file():
                model.ai.prompts.append(
                    to_detected_item(
                        path.stem,
                        detector_id=self.detector_id,
                        path=str(path.relative_to(root)),
                    )
                )

    def _scan_env_files(self, root: Path, model: ContextModel) -> None:
        for path in root.rglob(".env*"):
            if path.name.endswith(".example"):
                continue
            findings = scan_file_for_secrets(path, pepper=settings.api_key_pepper)
            model.data.secret_findings.extend(findings)
