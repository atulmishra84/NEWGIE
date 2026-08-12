"""Domain aggregates for Knowledge Intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from gie_contracts.knowledge import KnowledgeEdge, KnowledgeNode


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class KnowledgeIngestJob:
    job_id: UUID
    tenant_id: str
    status: IngestStatus
    idempotency_key: str
    requested_by: str
    node_count: int = 0
    edge_count: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None

    @classmethod
    def create(
        cls, *, tenant_id: str, idempotency_key: str, requested_by: str
    ) -> "KnowledgeIngestJob":
        return cls(
            job_id=uuid4(),
            tenant_id=tenant_id,
            status=IngestStatus.PENDING,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
        )


@dataclass
class VersionedGraph:
    """In-memory working set for a knowledge version."""

    version: str
    nodes: dict[str, KnowledgeNode] = field(default_factory=dict)
    edges: dict[str, KnowledgeEdge] = field(default_factory=dict)

    def add_node(self, node: KnowledgeNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: KnowledgeEdge) -> None:
        self.edges[edge.edge_id] = edge
