"""Async SQLAlchemy repositories for Knowledge Intelligence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from gie_contracts.knowledge import (
    Confidence,
    EvidenceRef,
    KnowledgeDiff,
    KnowledgeDomain,
    KnowledgeEdge,
    KnowledgeGraphSnapshot,
    KnowledgeNode,
    NodeKind,
    RelationType,
)
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from knowledge_intelligence.domain.ports import KnowledgeEdgeRepository, KnowledgeNodeRepository, VersionRepository
from knowledge_intelligence.settings import Settings


class Base(DeclarativeBase):
    pass


class NodeRow(Base):
    __tablename__ = "knowledge_nodes"
    node_id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String)
    domain: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, default=list)
    version: Mapped[str] = mapped_column(String, default="1.0.0")
    schema_version: Mapped[str] = mapped_column(String, default="gie.knowledge.v1")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EdgeRow(Base):
    __tablename__ = "knowledge_edges"
    edge_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String)
    relationship: Mapped[str] = mapped_column(String)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, default=list)
    version: Mapped[str] = mapped_column(String, default="1.0.0")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VersionRow(Base):
    __tablename__ = "knowledge_versions"
    version: Mapped[str] = mapped_column(String, primary_key=True)
    snapshot_id: Mapped[Any] = mapped_column(PGUUID(as_uuid=True))
    schema_version: Mapped[str] = mapped_column(String)
    node_count: Mapped[int] = mapped_column(Integer)
    edge_count: Mapped[int] = mapped_column(Integer)
    domains: Mapped[dict] = mapped_column(JSONB, default=list)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings):
    global _engine, _session_factory
    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_db(settings: Settings) -> None:
    init_engine(settings)
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db() -> bool:
    if _engine is None:
        return False
    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _to_node(row: NodeRow) -> KnowledgeNode:
    evidence = [EvidenceRef.model_validate(e) for e in (row.evidence or [])]
    return KnowledgeNode(
        node_id=row.node_id,
        kind=NodeKind(row.kind),
        domain=KnowledgeDomain(row.domain),
        title=row.title,
        summary=row.summary,
        body=row.body,
        tags=list(row.tags or []),
        attributes=dict(row.attributes or {}),
        evidence=evidence,
        version=row.version,
        schema_version=row.schema_version,
        confidence=Confidence(score=row.confidence_score, rationale=row.confidence_rationale),
        created_at=row.created_at,
        updated_at=row.updated_at,
        superseded_by=row.superseded_by,
        active=row.active,
    )


class PostgresNodeRepository(KnowledgeNodeRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._sf = session_factory or _session_factory

    async def upsert_nodes(self, nodes: list[KnowledgeNode]) -> int:
        assert self._sf
        async with self._sf() as session:
            for n in nodes:
                existing = await session.get(NodeRow, n.node_id)
                now = datetime.now(timezone.utc)
                if existing:
                    existing.kind = n.kind.value
                    existing.domain = n.domain.value
                    existing.title = n.title
                    existing.summary = n.summary
                    existing.body = n.body
                    existing.tags = n.tags
                    existing.attributes = n.attributes
                    existing.evidence = [e.model_dump(mode="json") for e in n.evidence]
                    existing.version = n.version
                    existing.confidence_score = n.confidence.score
                    existing.confidence_rationale = n.confidence.rationale
                    existing.active = n.active
                    existing.superseded_by = n.superseded_by
                    existing.updated_at = now
                else:
                    session.add(
                        NodeRow(
                            node_id=n.node_id,
                            kind=n.kind.value,
                            domain=n.domain.value,
                            title=n.title,
                            summary=n.summary,
                            body=n.body,
                            tags=n.tags,
                            attributes=n.attributes,
                            evidence=[e.model_dump(mode="json") for e in n.evidence],
                            version=n.version,
                            schema_version=n.schema_version,
                            confidence_score=n.confidence.score,
                            confidence_rationale=n.confidence.rationale,
                            active=n.active,
                            superseded_by=n.superseded_by,
                            created_at=n.created_at,
                            updated_at=now,
                        )
                    )
            await session.commit()
        return len(nodes)

    async def get_node(self, node_id: str, version: str | None = None) -> KnowledgeNode | None:
        assert self._sf
        async with self._sf() as session:
            row = await session.get(NodeRow, node_id)
            if not row:
                return None
            if version and row.version != version:
                stmt = select(NodeRow).where(NodeRow.node_id == node_id, NodeRow.version == version)
                row = (await session.execute(stmt)).scalar_one_or_none()
                if not row:
                    return None
            return _to_node(row)

    async def list_nodes(
        self,
        *,
        domain: str | None = None,
        kind: str | None = None,
        version: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeNode]:
        assert self._sf
        async with self._sf() as session:
            stmt = select(NodeRow).where(NodeRow.active.is_(True))
            if domain:
                stmt = stmt.where(NodeRow.domain == domain)
            if kind:
                stmt = stmt.where(NodeRow.kind == kind)
            if version:
                stmt = stmt.where(NodeRow.version == version)
            stmt = stmt.offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [_to_node(r) for r in rows]

    async def soft_delete(self, node_id: str) -> bool:
        assert self._sf
        async with self._sf() as session:
            row = await session.get(NodeRow, node_id)
            if not row:
                return False
            row.active = False
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return True


class PostgresEdgeRepository(KnowledgeEdgeRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._sf = session_factory or _session_factory

    async def upsert_edges(self, edges: list[KnowledgeEdge]) -> int:
        assert self._sf
        async with self._sf() as session:
            for e in edges:
                existing = await session.get(EdgeRow, e.edge_id)
                if existing:
                    existing.source_id = e.source_id
                    existing.target_id = e.target_id
                    existing.relationship = e.relationship.value
                    existing.weight = e.weight
                    existing.attributes = e.attributes
                    existing.evidence = [x.model_dump(mode="json") for x in e.evidence]
                    existing.version = e.version
                    existing.confidence_score = e.confidence.score
                else:
                    session.add(
                        EdgeRow(
                            edge_id=e.edge_id,
                            source_id=e.source_id,
                            target_id=e.target_id,
                            relationship=e.relationship.value,
                            weight=e.weight,
                            attributes=e.attributes,
                            evidence=[x.model_dump(mode="json") for x in e.evidence],
                            version=e.version,
                            confidence_score=e.confidence.score,
                            created_at=e.created_at,
                        )
                    )
            await session.commit()
        return len(edges)

    async def neighbors(self, node_id: str, depth: int = 1) -> list[KnowledgeEdge]:
        assert self._sf
        async with self._sf() as session:
            stmt = select(EdgeRow).where((EdgeRow.source_id == node_id) | (EdgeRow.target_id == node_id))
            rows = (await session.execute(stmt)).scalars().all()
            return [
                KnowledgeEdge(
                    edge_id=r.edge_id,
                    source_id=r.source_id,
                    target_id=r.target_id,
                    relationship=RelationType(r.relationship),
                    weight=r.weight,
                    attributes=dict(r.attributes or {}),
                    version=r.version,
                    confidence=Confidence(score=r.confidence_score),
                    created_at=r.created_at,
                )
                for r in rows
            ]


class PostgresVersionRepository(VersionRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._sf = session_factory or _session_factory

    async def publish(self, version: str, checksum: str, node_count: int, edge_count: int) -> KnowledgeGraphSnapshot:
        assert self._sf
        snap = KnowledgeGraphSnapshot(version=version, node_count=node_count, edge_count=edge_count, checksum=checksum)
        async with self._sf() as session:
            session.add(
                VersionRow(
                    version=version,
                    snapshot_id=snap.snapshot_id,
                    schema_version=snap.schema_version,
                    node_count=node_count,
                    edge_count=edge_count,
                    domains=[],
                    checksum=checksum,
                    created_at=snap.created_at,
                )
            )
            await session.commit()
        return snap

    async def latest(self) -> KnowledgeGraphSnapshot | None:
        assert self._sf
        async with self._sf() as session:
            stmt = select(VersionRow).order_by(VersionRow.created_at.desc()).limit(1)
            row = (await session.execute(stmt)).scalar_one_or_none()
            if not row:
                return None
            return KnowledgeGraphSnapshot(
                snapshot_id=row.snapshot_id,
                version=row.version,
                schema_version=row.schema_version,
                node_count=row.node_count,
                edge_count=row.edge_count,
                checksum=row.checksum,
                created_at=row.created_at,
            )

    async def get(self, version: str) -> KnowledgeGraphSnapshot | None:
        assert self._sf
        async with self._sf() as session:
            row = await session.get(VersionRow, version)
            if not row:
                return None
            return KnowledgeGraphSnapshot(
                snapshot_id=row.snapshot_id,
                version=row.version,
                schema_version=row.schema_version,
                node_count=row.node_count,
                edge_count=row.edge_count,
                checksum=row.checksum,
                created_at=row.created_at,
            )

    async def diff(self, from_version: str, to_version: str) -> KnowledgeDiff:
        # Simplified: versions table stores counts; node-level diff via list comparison in app layer for memory mode.
        return KnowledgeDiff(from_version=from_version, to_version=to_version)
