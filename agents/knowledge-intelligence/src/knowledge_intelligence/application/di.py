"""Dependency injection container for Knowledge Intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from knowledge_intelligence.application.commands.reindex import ReindexHandler
from knowledge_intelligence.application.commands.upsert_knowledge import UpsertKnowledgeHandler
from knowledge_intelligence.application.queries.diff_versions import DiffVersionsHandler
from knowledge_intelligence.application.queries.get_node import GetNodeHandler
from knowledge_intelligence.application.query_engine import HybridQueryEngine
from knowledge_intelligence.domain.ports import (
    CacheStore,
    EmbeddingService,
    EventPublisher,
    GraphRepository,
    KnowledgeEdgeRepository,
    KnowledgeNodeRepository,
    VectorStore,
    VersionRepository,
)
from knowledge_intelligence.settings import Settings, get_settings


@dataclass
class Container:
    settings: Settings
    nodes: KnowledgeNodeRepository
    edges: KnowledgeEdgeRepository
    graph: GraphRepository
    vectors: VectorStore
    embeddings: EmbeddingService
    versions: VersionRepository
    cache: CacheStore
    events: EventPublisher

    @property
    def query_engine(self) -> HybridQueryEngine:
        return HybridQueryEngine(
            nodes=self.nodes,
            vectors=self.vectors,
            embeddings=self.embeddings,
            graph=self.graph,
            cache=self.cache,
            settings=self.settings,
        )

    @property
    def upsert(self) -> UpsertKnowledgeHandler:
        return UpsertKnowledgeHandler(
            nodes=self.nodes,
            edges=self.edges,
            graph=self.graph,
            vectors=self.vectors,
            embeddings=self.embeddings,
            versions=self.versions,
            events=self.events,
            settings=self.settings,
        )

    @property
    def reindex(self) -> ReindexHandler:
        return ReindexHandler(nodes=self.nodes, vectors=self.vectors, embeddings=self.embeddings, settings=self.settings)

    @property
    def get_node(self) -> GetNodeHandler:
        return GetNodeHandler(self.nodes)

    @property
    def diff_versions(self) -> DiffVersionsHandler:
        return DiffVersionsHandler(self.versions)


_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
