"""Secret detection with fingerprinting — never stores raw values."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from gie_contracts.context_model import Confidence, EvidenceRef, SecretFinding, Severity

SECRET_PATTERNS: list[tuple[str, re.Pattern[str], Severity]] = [
    (
        "openai_api_key",
        re.compile(r"OPENAI_API_KEY\s*=\s*(sk-[A-Za-z0-9_-]{8,})", re.IGNORECASE),
        Severity.CRITICAL,
    ),
    (
        "anthropic_api_key",
        re.compile(
            r"ANTHROPIC_API_KEY\s*=\s*(sk-ant-[A-Za-z0-9_-]{8,})", re.IGNORECASE
        ),
        Severity.CRITICAL,
    ),
    (
        "aws_access_key",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        Severity.HIGH,
    ),
    (
        "generic_bearer",
        re.compile(r"Bearer\s+([A-Za-z0-9._-]{20,})"),
        Severity.MEDIUM,
    ),
]


@dataclass(frozen=True)
class SecretMatch:
    kind: str
    location: str
    fingerprint: str
    severity: Severity
    line_number: int | None = None


def fingerprint_secret(raw: str, *, pepper: str = "") -> str:
    """Return stable SHA-256 fingerprint; raw value is never persisted."""
    digest = hashlib.sha256(f"{pepper}:{raw}".encode()).hexdigest()
    return f"sha256:{digest[:32]}"


def scan_text_for_secrets(
    text: str,
    *,
    location: str,
    pepper: str = "",
    detector_id: str = "secrets.detector.v1",
) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    lines = text.splitlines()
    for kind, pattern, severity in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(1) if match.lastindex else match.group(0)
            line_no = text[: match.start()].count("\n") + 1
            fp = fingerprint_secret(raw, pepper=pepper)
            findings.append(
                SecretFinding(
                    kind=kind,
                    location=location,
                    fingerprint=fp,
                    severity=severity,
                    confidence=Confidence(score=0.95, rationale="pattern match"),
                    evidence=[
                        EvidenceRef(
                            evidence_id=f"{location}:{line_no}:{kind}",
                            path=location,
                            start_line=line_no,
                            end_line=line_no,
                            detector_id=detector_id,
                            excerpt_hash=hashlib.sha256(
                                lines[line_no - 1].encode()
                            ).hexdigest()[:16],
                        )
                    ],
                )
            )
    return findings


def scan_file_for_secrets(path: Path, *, pepper: str = "") -> list[SecretFinding]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return scan_text_for_secrets(text, location=str(path), pepper=pepper)
