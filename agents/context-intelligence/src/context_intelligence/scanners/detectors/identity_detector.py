"""Identity provider detection."""

from __future__ import annotations

from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import (
    BaseDetector,
    iter_files,
    read_text,
)
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

PROVIDERS: list[tuple[str, list[str], float]] = [
    ("auth0", ["auth0", "AUTH0_DOMAIN", "auth0.com"], 0.9),
    ("okta", ["okta", "OKTA_DOMAIN", "okta.com"], 0.9),
    ("azure-ad", ["azure.ad", "login.microsoftonline.com", "AZURE_AD", "Entra"], 0.88),
    ("cognito", ["cognito", "COGNITO_USER_POOL", "aws cognito"], 0.88),
    ("keycloak", ["keycloak"], 0.85),
    ("firebase-auth", ["firebase.auth", "firebase_auth"], 0.85),
]


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class IdentityDetector(BaseDetector):
    detector_id = "identity.detector.v1"
    section = FindingSection.SECURITY
    default_category = FindingCategory.IDENTITY_PROVIDER

    async def detect(self, workspace_path: Path) -> list:
        findings = []
        seen: set[str] = set()

        for path in iter_files(
            workspace_path,
            extensions={
                ".py",
                ".ts",
                ".js",
                ".yaml",
                ".yml",
                ".json",
                ".env",
                ".toml",
                ".xml",
            },
        ):
            text = read_text(path)
            if not text:
                continue
            lowered = text.lower()
            for name, needles, confidence in PROVIDERS:
                if name in seen:
                    continue
                if any(n.lower() in lowered for n in needles):
                    seen.add(name)
                    findings.append(
                        self.finding(
                            name=name,
                            confidence=confidence,
                            rationale="Identity provider reference",
                            path=str(path),
                        )
                    )
        return findings
