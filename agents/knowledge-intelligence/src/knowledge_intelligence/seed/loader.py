"""Load built-in knowledge corpora into the graph + vector index."""

from __future__ import annotations

import json
import os
from pathlib import Path

from gie_contracts.knowledge import KnowledgeEdge, KnowledgeNode, KnowledgeUpsertRequest
from gie_observability.logging import get_logger

from knowledge_intelligence.application.di import Container

logger = get_logger(__name__)


def seed_data_dir() -> Path:
    """Resolve seed directory across editable install, Docker image, and source tree."""
    candidates: list[Path] = []
    env = os.environ.get("GIE_KNOWLEDGE_SEED_PATH")
    if env:
        candidates.append(Path(env))
    # Source layout: .../agents/knowledge-intelligence/src/knowledge_intelligence/seed/loader.py
    here = Path(__file__).resolve()
    candidates.extend(
        [
            here.parents[3] / "data" / "seed",  # agent root / data / seed
            here.parents[2] / "data" / "seed",
            Path.cwd() / "data" / "seed",
            Path.cwd() / "agents" / "knowledge-intelligence" / "data" / "seed",
            Path("/app/data/seed"),
        ]
    )
    for path in candidates:
        if (path / "corpus_v1.json").exists():
            return path
    return candidates[0]


async def seed_builtin_knowledge(container: Container) -> int:
    corpus_path = seed_data_dir() / "corpus_v1.json"
    if not corpus_path.exists():
        logger.warning("seed_corpus_missing", path=str(corpus_path))
        return 0
    raw = json.loads(corpus_path.read_text())
    nodes = [KnowledgeNode.model_validate(n) for n in raw.get("nodes", [])]
    edges = [KnowledgeEdge.model_validate(e) for e in raw.get("edges", [])]
    existing = await container.nodes.list_nodes(limit=1)
    if existing:
        logger.info("seed_skipped_already_populated")
        return 0
    result = await container.upsert.handle(
        KnowledgeUpsertRequest(
            nodes=nodes,
            edges=edges,
            publish_version=True,
            version_label=raw.get("version", "1.0.0"),
        ),
        tenant_id="system",
        actor="seed-loader",
        correlation_id="seed",
    )
    logger.info("seed_completed", **result)
    return int(result.get("nodes_upserted", 0))
