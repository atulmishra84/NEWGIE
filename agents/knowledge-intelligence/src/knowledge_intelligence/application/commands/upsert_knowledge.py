"""Upsert knowledge nodes/edges with optional version publish."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from gie_contracts.knowledge import KnowledgeUpsertRequest
from gie_contracts.knowledge_events import KnowledgeNodeUpserted, KnowledgeVersionPublished
from gie_observability.logging import get_logger

from knowledge_intelligence.domain.ports import (
    EmbeddingService,
    EventPublisher,
    GraphRepository,
    KnowledgeEdgeRepository,
    KnowledgeNodeRepository,
    VectorStore,
    VersionRepository,
)
from knowledge_intelligence.settings import Settings

logger = get_logger(__name__)


class UpsertKnowledgeHandler:
    def __init__(
        self,
        *,
        nodes: KnowledgeNodeRepository,
        edges: KnowledgeEdgeRepository,
        graph: GraphRepository,
        vectors: VectorStore,
        embeddings: EmbeddingService,
        versions: VersionRepository,
        events: EventPublisher,
        settings: Settings,
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._graph = graph
        self._vectors = vectors
        self._embeddings = embeddings
        self._versions = versions
        self._events = events
        self._settings = settings

    async def handle(
        self,
        request: KnowledgeUpsertRequest,
        *,
        tenant_id: str,
        actor: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        n = await self._nodes.upsert_nodes(request.nodes)
        e = await self._edges.upsert_edges(request.edges)
        if request.nodes:
            await self._graph.project_nodes(request.nodes)
            texts = [f"{x.title}\n{x.summary}\n{x.body}" for x in request.nodes]
            vecs = await self._embeddings.embed(texts)
            payloads = [
                {
                    "node_id": x.node_id,
                    "domain": x.domain.value,
                    "kind": x.kind.value,
                    "version": x.version,
                    "title": x.title,
                }
                for x in request.nodes
            ]
            await self._vectors.upsert([x.node_id for x in request.nodes], vecs, payloads)
            for node in request.nodes:
                evt = KnowledgeNodeUpserted(
                    tenant_id=tenant_id,
                    correlation_id=correlation_id,
                    producer_version=self._settings.agent_version,
                    node_id=node.node_id,
                    domain=node.domain,
                    version=node.version,
                )
                await self._events.publish(
                    self._settings.kafka_topic_events,
                    evt.model_dump(mode="json"),
                    key=node.node_id,
                )
        if request.edges:
            await self._graph.project_edges(request.edges)

        snapshot = None
        if request.publish_version:
            version = request.version_label or self._next_version()
            checksum = hashlib.sha256(
                json.dumps(
                    {"nodes": [n.node_id for n in request.nodes], "edges": [e.edge_id for e in request.edges]},
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            snapshot = await self._versions.publish(version, checksum, n, e)
            pub = KnowledgeVersionPublished(
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                producer_version=self._settings.agent_version,
                version=version,
                node_count=n,
                edge_count=e,
                checksum=checksum,
            )
            await self._events.publish(self._settings.kafka_topic_events, pub.model_dump(mode="json"), key=version)

        logger.info("knowledge_upserted", nodes=n, edges=e, actor=actor, tenant_id=tenant_id)
        return {
            "nodes_upserted": n,
            "edges_upserted": e,
            "version": snapshot.version if snapshot else None,
            "snapshot_id": str(snapshot.snapshot_id) if snapshot else None,
        }

    def _next_version(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
