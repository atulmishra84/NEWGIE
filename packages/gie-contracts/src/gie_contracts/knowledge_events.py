"""Kafka / outbox events for Knowledge Intelligence Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from gie_contracts.knowledge import KnowledgeDomain


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    causation_id: str | None = None
    producer: str = "knowledge-intelligence"
    producer_version: str


class KnowledgeNodeUpserted(KnowledgeEventEnvelope):
    event_type: Literal["knowledge.node.upserted"] = "knowledge.node.upserted"
    node_id: str
    domain: KnowledgeDomain
    version: str


class KnowledgeEdgeUpserted(KnowledgeEventEnvelope):
    event_type: Literal["knowledge.edge.upserted"] = "knowledge.edge.upserted"
    edge_id: str
    source_id: str
    target_id: str
    relationship: str


class KnowledgeVersionPublished(KnowledgeEventEnvelope):
    event_type: Literal["knowledge.version.published"] = "knowledge.version.published"
    version: str
    node_count: int
    edge_count: int
    checksum: str | None = None


class KnowledgeQueryExecuted(KnowledgeEventEnvelope):
    event_type: Literal["knowledge.query.executed"] = "knowledge.query.executed"
    query_id: UUID
    hit_count: int
    confidence: float
    duration_ms: int
    domains: list[str] = Field(default_factory=list)


class KnowledgeReindexRequested(KnowledgeEventEnvelope):
    event_type: Literal["knowledge.reindex.requested"] = "knowledge.reindex.requested"
    domains: list[KnowledgeDomain] = Field(default_factory=list)
    full: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)
