"""Qdrant vector store for evidence with hash embedding fallback."""

from __future__ import annotations

import hashlib
import struct
from typing import Any
from uuid import UUID

from gie_observability.logging import get_logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from context_intelligence.domain.ports import EvidenceVectorStore
from context_intelligence.settings import Settings, get_settings

logger = get_logger(__name__)

VECTOR_SIZE = 384


def hash_embed(text: str, dim: int = VECTOR_SIZE) -> list[float]:
    """Deterministic pseudo-embedding from SHA-256 chunks."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dim:
        for i in range(0, len(digest) - 3, 4):
            chunk = digest[i : i + 4]
            value = struct.unpack("!i", chunk)[0]
            values.append((value % 10000) / 10000.0)
            if len(values) >= dim:
                break
        digest = hashlib.sha256(digest).digest()
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values]


class QdrantEvidenceVectorStore(EvidenceVectorStore):
    def __init__(
        self,
        client: AsyncQdrantClient,
        collection: str,
        *,
        embedder: Any | None = None,
    ) -> None:
        self._client = client
        self._collection = collection
        self._embedder = embedder
        self._initialized = False

    @classmethod
    def from_settings(cls, settings: Settings | None = None, embedder: Any | None = None) -> QdrantEvidenceVectorStore:
        cfg = settings or get_settings()
        client = AsyncQdrantClient(url=cfg.qdrant_url)
        return cls(client, cfg.qdrant_collection, embedder=embedder)

    async def _ensure_collection(self) -> None:
        if self._initialized:
            return
        collections = await self._client.get_collections()
        names = {c.name for c in collections.collections}
        if self._collection not in names:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
            )
        self._initialized = True

    async def _embed(self, text: str) -> list[float]:
        if self._embedder is not None:
            try:
                result = self._embedder.embed(text)
                if hasattr(result, "__await__"):
                    result = await result
                if isinstance(result, list) and result and isinstance(result[0], (int, float)):
                    return [float(x) for x in result]
            except Exception:
                logger.warning("embedder_failed_using_hash_fallback")
        return hash_embed(text)

    async def upsert_evidence(
        self,
        *,
        evidence_id: str,
        tenant_id: str,
        scan_id: UUID,
        text: str,
        metadata: dict[str, Any],
    ) -> None:
        await self._ensure_collection()
        vector = await self._embed(text)
        point_id = int(hashlib.sha256(evidence_id.encode()).hexdigest()[:16], 16) % (2**63 - 1)
        payload = {
            "evidence_id": evidence_id,
            "tenant_id": tenant_id,
            "scan_id": str(scan_id),
            **metadata,
        }
        await self._client.upsert(
            collection_name=self._collection,
            points=[
                qmodels.PointStruct(id=point_id, vector=vector, payload=payload),
            ],
        )

    async def ping(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False
