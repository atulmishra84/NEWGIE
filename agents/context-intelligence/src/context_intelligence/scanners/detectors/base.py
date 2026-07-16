"""Shared detector helpers."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from gie_contracts.context_model import EvidenceRef

from context_intelligence.domain.findings import (
    DetectionFinding,
    FindingCategory,
    FindingSection,
)

TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".txt",
        ".env",
        ".ini",
        ".cfg",
        ".sh",
        ".rb",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".cs",
        ".sql",
        ".prompt",
    }
)
MAX_FILE_BYTES = 512_000
SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".gie",
    }
)


class BaseDetector(ABC):
    detector_id: str
    section: FindingSection
    default_category: FindingCategory

    @abstractmethod
    async def detect(self, workspace_path: Path) -> list[DetectionFinding]:
        raise NotImplementedError

    def finding(
        self,
        *,
        category: FindingCategory | None = None,
        name: str,
        version: str | None = None,
        confidence: float = 0.8,
        rationale: str | None = None,
        path: str | None = None,
        line: int | None = None,
        attributes: dict | None = None,
        severity=None,
        fingerprint: str | None = None,
        location: str | None = None,
    ) -> DetectionFinding:
        evidence: list[EvidenceRef] = []
        if path:
            evidence.append(
                EvidenceRef(
                    evidence_id=f"{self.detector_id}:{path}:{line or 0}",
                    path=path,
                    start_line=line,
                    end_line=line,
                    detector_id=self.detector_id,
                )
            )
        return DetectionFinding(
            detector_id=self.detector_id,
            section=self.section,
            category=category or self.default_category,
            name=name,
            version=version,
            confidence=confidence,
            rationale=rationale,
            evidence=evidence,
            attributes=attributes or {},
            severity=severity,
            fingerprint=fingerprint,
            location=location or path,
        )


def iter_files(
    root: Path,
    *,
    extensions: Iterable[str] | None = None,
    names: Iterable[str] | None = None,
) -> Iterable[Path]:
    ext_set = {e if e.startswith(".") else f".{e}" for e in extensions} if extensions else None
    name_set = set(names) if names else None
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if ext_set is not None and path.suffix.lower() not in ext_set:
            if name_set is None or path.name not in name_set:
                continue
        if name_set is not None and path.name in name_set:
            yield path
            continue
        if ext_set is None or path.suffix.lower() in ext_set:
            yield path


def read_text(path: Path, *, max_bytes: int = MAX_FILE_BYTES) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def search_patterns(
    text: str,
    patterns: list[tuple[re.Pattern[str], str, float]],
) -> list[tuple[str, float, re.Match[str]]]:
    hits: list[tuple[str, float, re.Match[str]]] = []
    for pattern, name, confidence in patterns:
        for match in pattern.finditer(text):
            hits.append((name, confidence, match))
    return hits
