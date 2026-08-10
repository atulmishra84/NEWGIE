"""Hexagonal ports for Knowledge Intelligence Agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from gie_contracts.knowledge import (
    ExplainableRetrievalResult,
    KnowledgeDiff,
    KnowledgeEdge,
    KnowledgeGraphSnapshot,
    KnowledgeNode,
    KnowledgeQueryRequest,
    KnowledgeUpsertRequest,
)


class KnowledgeNodeRepository(ABC):
    @abstractmethod
    async def upsert_nodes(self, nodes: list[KnowledgeNode]) -> int: ...

    @abstractmethod
    async def get_node(
        self, node_id: str, version: str | None = None
    ) -> KnowledgeNode | None: ...

    @abstractmethod
    async def list_nodes(
        self,
        *,
        domain: str | None = None,
        kind: str | None = None,
        version: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeNode]: ...

    @abstractmethod
    async def soft_delete(self, node_id: str) -> bool: ...


class KnowledgeEdgeRepository(ABC):
    @abstractmethod
    async def upsert_edges(self, edges: list[KnowledgeEdge]) -> int: ...

    @abstractmethod
    async def neighbors(self, node_id: str, depth: int = 1) -> list[KnowledgeEdge]: ...


class GraphRepository(ABC):
    @abstractmethod
    async def project_nodes(self, nodes: list[KnowledgeNode]) -> None: ...

    @abstractmethod
    async def project_edges(self, edges: list[KnowledgeEdge]) -> None: ...

    @abstractmethod
    async def shortest_paths(
        self, source_id: str, target_id: str, max_depth: int = 4
    ) -> list[list[str]]: ...

    @abstractmethod
    async def expand(
        self, node_ids: list[str], hops: int = 1
    ) -> tuple[list[str], list[dict[str, Any]]]: ...

    @abstractmethod
    async def ping(self) -> bool: ...

    @abstractmethod
    async def close(self) -> None: ...


class EmbeddingService(ABC):
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(ABC):
    @abstractmethod
    async def upsert(
        self, ids: list[str], vectors: list[list[float]], payloads: list[dict[str, Any]]
    ) -> None: ...

    @abstractmethod
    async def search(
        self, vector: list[float], top_k: int, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def ping(self) -> bool: ...


class VersionRepository(ABC):
    @abstractmethod
    async def publish(
        self, version: str, checksum: str, node_count: int, edge_count: int
    ) -> KnowledgeGraphSnapshot: ...

    @abstractmethod
    async def latest(self) -> KnowledgeGraphSnapshot | None: ...

    @abstractmethod
    async def get(self, version: str) -> KnowledgeGraphSnapshot | None: ...

    @abstractmethod
    async def diff(self, from_version: str, to_version: str) -> KnowledgeDiff: ...


class CacheStore(ABC):
    @abstractmethod
    async def get_json(self, key: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class EventPublisher(ABC):
    @abstractmethod
    async def publish(
        self, topic: str, event: dict[str, Any], key: str | None = None
    ) -> None: ...


class KnowledgeQueryEngine(Protocol):
    async def query(
        self, request: KnowledgeQueryRequest, *, tenant_id: str, correlation_id: str
    ) -> ExplainableRetrievalResult: ...


class KnowledgeCommandService(Protocol):
    async def upsert(
        self,
        request: KnowledgeUpsertRequest,
        *,
        tenant_id: str,
        actor: str,
        correlation_id: str,
    ) -> dict[str, Any]: ...
