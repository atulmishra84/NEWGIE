"""Language detection by extension and shebang."""

from __future__ import annotations

from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import (
    BaseDetector,
    iter_files,
    read_text,
)
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

EXTENSION_MAP: dict[str, tuple[str, float]] = {
    ".py": ("python", 0.9),
    ".js": ("javascript", 0.85),
    ".jsx": ("javascript", 0.85),
    ".ts": ("typescript", 0.9),
    ".tsx": ("typescript", 0.9),
    ".go": ("go", 0.9),
    ".rs": ("rust", 0.9),
    ".java": ("java", 0.9),
    ".kt": ("kotlin", 0.9),
    ".cs": ("csharp", 0.9),
    ".rb": ("ruby", 0.85),
    ".php": ("php", 0.85),
    ".swift": ("swift", 0.9),
    ".scala": ("scala", 0.85),
    ".sh": ("shell", 0.7),
    ".sql": ("sql", 0.75),
}

SHEBANG_MAP: dict[str, tuple[str, float]] = {
    "python": ("python", 0.95),
    "python3": ("python", 0.95),
    "node": ("javascript", 0.9),
    "bash": ("shell", 0.9),
    "sh": ("shell", 0.85),
    "ruby": ("ruby", 0.9),
}


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class LanguageDetector(BaseDetector):
    detector_id = "language.detector.v1"
    section = FindingSection.IDENTITY
    default_category = FindingCategory.LANGUAGE

    async def detect(self, workspace_path: Path) -> list:
        counts: dict[str, tuple[int, float, str | None]] = {}

        for path in iter_files(workspace_path, extensions=EXTENSION_MAP.keys()):
            lang, conf = EXTENSION_MAP.get(path.suffix.lower(), ("unknown", 0.5))
            prev = counts.get(lang)
            if prev is None or prev[0] < 1:
                counts[lang] = (prev[0] + 1 if prev else 1, conf, str(path))

        for path in iter_files(workspace_path, extensions={".py", ".sh", ".rb", ".pl"}):
            text = read_text(path, max_bytes=256)
            if not text:
                continue
            first = text.splitlines()[0] if text.splitlines() else ""
            if first.startswith("#!"):
                interpreter = Path(first[2:].strip().split()[0]).name
                mapped = SHEBANG_MAP.get(interpreter)
                if mapped:
                    lang, conf = mapped
                    counts[lang] = (
                        counts.get(lang, (0, 0, None))[0] + 2,
                        conf,
                        str(path),
                    )

        findings = []
        for lang, (count, conf, sample) in counts.items():
            if lang == "unknown":
                continue
            score = min(0.99, conf + min(count, 20) * 0.005)
            findings.append(
                self.finding(
                    name=lang,
                    confidence=score,
                    rationale=f"{count} file(s) with {lang} markers",
                    path=sample,
                    attributes={"file_count": count},
                )
            )
        return findings
