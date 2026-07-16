"""Vector database detection."""

from __future__ import annotations

from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, iter_files, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

VECTOR_DBS: list[tuple[str, list[str], float]] = [
    ("qdrant", ["qdrant", "QdrantClient"], 0.9),
    ("pinecone", ["pinecone"], 0.9),
    ("weaviate", ["weaviate"], 0.9),
    ("chroma", ["chromadb", "chroma"], 0.88),
    ("milvus", ["milvus", "pymilvus"], 0.9),
    ("pgvector", ["pgvector", "postgresql+psycopg"], 0.85),
    ("faiss", ["faiss"], 0.8),
]


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class VectorDbDetector(BaseDetector):
    detector_id = "vector_db.detector.v1"
    section = FindingSection.DATA
    default_category = FindingCategory.VECTOR_DATABASE

    async def detect(self, workspace_path: Path) -> list:
        findings = []
        seen: set[str] = set()

        for path in iter_files(
            workspace_path,
            extensions={".py", ".ts", ".js", ".yaml", ".yml", ".env", ".toml", ".txt", ".json"},
        ):
            text = read_text(path)
            if not text:
                continue
            lowered = text.lower()
            for name, needles, confidence in VECTOR_DBS:
                if name in seen:
                    continue
                if any(n.lower() in lowered for n in needles):
                    seen.add(name)
                    findings.append(
                        self.finding(
                            name=name,
                            confidence=confidence,
                            rationale="Vector store reference",
                            path=str(path),
                        )
                    )
        return findings
