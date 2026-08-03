"""Qdrant vector store for knowledge embeddings."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from knowledge_intelligence.domain.ports import VectorStore
from knowledge_intelligence.settings import Settings


class QdrantKnowledgeStore(VectorStore):
    def __init__(self, url: str, collection: str, dim: int) -> None:
        self._client = QdrantClient(url=url, prefer_grpc=False)
        self._collection = collection
        self._dim = dim
        self._ensure_collection()

    @classmethod
    def from_settings(cls, settings: Settings) -> "QdrantKnowledgeStore":
        return cls(settings.qdrant_url, settings.qdrant_collection, settings.embedding_dim)

    def _ensure_collection(self) -> None:
        names = [c.name for c in self._client.get_collections().collections]
        if self._collection not in names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qm.VectorParams(size=self._dim, distance=qm.Distance.COSINE),
            )

    async def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict[str, Any]]) -> None:
        points = [
            qm.PointStruct(id=self._stable_id(i), vector=v, payload={**p, "node_id": i})
            for i, v, p in zip(ids, vectors, payloads)
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    async def search(self, vector: list[float], top_k: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        qfilter = None
        if filters:
            must = []
            if "domain" in filters:
                must.append(qm.FieldCondition(key="domain", match=qm.MatchAny(any=filters["domain"])))
            if "kind" in filters:
                must.append(qm.FieldCondition(key="kind", match=qm.MatchAny(any=filters["kind"])))
            if "version" in filters:
                must.append(qm.FieldCondition(key="version", match=qm.MatchValue(value=filters["version"])))
            if must:
                qfilter = qm.Filter(must=must)
        hits = self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=top_k,
            query_filter=qfilter,
        )
        out = []
        for h in hits:
            payload = h.payload or {}
            out.append({"id": payload.get("node_id", str(h.id)), "score": float(h.score), "payload": payload})
        return out

    async def ping(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def _stable_id(self, node_id: str) -> int:
        # Qdrant unsigned int id from hash
        return int.from_bytes(node_id.encode("utf-8")[:8].ljust(8, b"\0"), "big") % (2**63 - 1)
