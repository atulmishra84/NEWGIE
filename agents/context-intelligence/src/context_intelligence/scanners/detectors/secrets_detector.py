"""Secret detection with fingerprint-only storage."""

from __future__ import annotations

import os
from pathlib import Path

from gie_contracts.context_model import Severity

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.domain.secrets_detector import (
    scan_file_for_secrets,
    scan_text_for_secrets,
)
from context_intelligence.scanners.detectors.base import (
    BaseDetector,
    iter_files,
    read_text,
)
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class SecretsDetector(BaseDetector):
    detector_id = "secrets.detector.v1"
    section = FindingSection.DATA
    default_category = FindingCategory.SECRET

    async def detect(self, workspace_path: Path) -> list:
        pepper = os.environ.get("API_KEY_PEPPER", "")
        findings = []

        for path in iter_files(
            workspace_path,
            extensions={
                ".py",
                ".js",
                ".ts",
                ".env",
                ".yaml",
                ".yml",
                ".json",
                ".toml",
                ".cfg",
                ".ini",
                ".txt",
            },
        ):
            for secret in scan_file_for_secrets(path, pepper=pepper):
                findings.append(
                    self.finding(
                        name=secret.kind,
                        confidence=secret.confidence.score,
                        rationale="Pattern-based secret fingerprint",
                        path=secret.location,
                        severity=secret.severity,
                        fingerprint=secret.fingerprint,
                        location=secret.location,
                        attributes={"kind": secret.kind},
                    )
                )

        for path in workspace_path.rglob(".env*"):
            if not path.is_file():
                continue
            text = read_text(path)
            if not text:
                continue
            for secret in scan_text_for_secrets(
                text, location=str(path), pepper=pepper, detector_id=self.detector_id
            ):
                findings.append(
                    self.finding(
                        name=secret.kind,
                        confidence=secret.confidence.score,
                        rationale="Env file secret fingerprint",
                        path=secret.location,
                        severity=secret.severity or Severity.HIGH,
                        fingerprint=secret.fingerprint,
                        location=secret.location,
                        attributes={"kind": secret.kind},
                    )
                )
        return findings
