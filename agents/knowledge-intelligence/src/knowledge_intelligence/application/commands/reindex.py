"""Rebuild vector index from persisted nodes."""

from __future__ import annotations

from gie_observability.logging import get_logger

from knowledge_intelligence.domain.ports import EmbeddingService, KnowledgeNodeRepository, VectorStore
from knowledge_intelligence.settings import Settings

logger = get_logger(__name__)


class ReindexHandler:
    def __init__(
        self,
        *,
        nodes: KnowledgeNodeRepository,
        vectors: VectorStore,
        embeddings: EmbeddingService,
        settings: Settings,
    ) -> None:
        self._nodes = nodes
        self._vectors = vectors
        self._embeddings = embeddings
        self._settings = settings

    async def handle(self, *, domain: str | None = None, batch_size: int = 100) -> dict[str, int]:
        offset = 0
        total = 0
        while True:
            batch = await self._nodes.list_nodes(domain=domain, limit=batch_size, offset=offset)
            if not batch:
                break
            texts = [f"{n.title}\n{n.summary}\n{n.body}" for n in batch]
            vecs = await self._embeddings.embed(texts)
            payloads = [
                {
                    "node_id": n.node_id,
                    "domain": n.domain.value,
                    "kind": n.kind.value,
                    "version": n.version,
                    "title": n.title,
                }
                for n in batch
            ]
            await self._vectors.upsert([n.node_id for n in batch], vecs, payloads)
            total += len(batch)
            offset += batch_size
        logger.info("knowledge_reindexed", total=total, domain=domain)
        return {"reindexed": total}
