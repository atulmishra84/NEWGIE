"""Outbound port protocols for Context Intelligence."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from gie_contracts.context_model import ContextModel, GraphSection
from gie_contracts.events import EventEnvelope
from gie_contracts.sources import ScanSource

from context_intelligence.domain.entities import ContextScan, ScanStatus
from context_intelligence.domain.findings import DetectionFinding


@runtime_checkable
class ScanWorkspace(Protocol):
    """Temporary filesystem workspace for a single scan."""

    @property
    def path(self) -> Path: ...

    async def cleanup(self) -> None: ...


@runtime_checkable
class SourceReader(Protocol):
    """Materializes a scan source into a workspace directory."""

    async def materialize(self, source: ScanSource, workspace: ScanWorkspace) -> str:
        """Return a content digest for provenance."""
        ...


@runtime_checkable
class Detector(Protocol):
    """Pluggable detector that emits normalized findings."""

    @property
    def detector_id(self) -> str: ...

    async def detect(self, workspace_path: Path) -> Sequence[DetectionFinding]: ...


@runtime_checkable
class ContextRepository(Protocol):
    """Persistence for scans and context models."""

    async def save_scan(self, scan: ContextScan) -> None: ...

    async def update_scan(self, scan: ContextScan) -> None: ...

    async def get_scan(self, scan_id: UUID, tenant_id: str) -> ContextScan | None: ...

    async def get_scan_by_idempotency_key(
        self,
        tenant_id: str,
        idempotency_key: str,
    ) -> ContextScan | None: ...

    async def list_scans(
        self,
        tenant_id: str,
        *,
        status: ScanStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContextScan]: ...

    async def save_model(self, model: ContextModel) -> None: ...

    async def get_model(
        self, model_id: UUID, tenant_id: str
    ) -> ContextModel | None: ...

    async def get_model_by_scan(
        self, scan_id: UUID, tenant_id: str
    ) -> ContextModel | None: ...

    async def list_model_versions(
        self,
        tenant_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ContextModel]: ...


@runtime_checkable
class GraphRepository(Protocol):
    """Graph projection store (Neo4j)."""

    async def upsert_graph(
        self,
        scan_id: UUID,
        tenant_id: str,
        graph: GraphSection,
    ) -> None: ...


@runtime_checkable
class EvidenceVectorStore(Protocol):
    """Vector index for evidence retrieval."""

    async def upsert_evidence(
        self,
        scan_id: UUID,
        tenant_id: str,
        findings: Sequence[DetectionFinding],
    ) -> int: ...


@runtime_checkable
class EventPublisher(Protocol):
    """Publishes domain events to Kafka or outbox."""

    async def publish(self, event: EventEnvelope) -> None: ...


@runtime_checkable
class CacheStore(Protocol):
    """Redis-backed cache for hot context models."""

    async def get(self, key: str) -> bytes | None: ...

    async def set(
        self, key: str, value: bytes, ttl_seconds: int | None = None
    ) -> None: ...

    async def delete(self, key: str) -> None: ...


@runtime_checkable
class ScanEnqueuer(Protocol):
    """Background job enqueue port (Celery / worker)."""

    async def enqueue_execute(
        self, scan_id: UUID, tenant_id: str, correlation_id: str
    ) -> None: ...


class WorkspaceFactory(Protocol):
    """Creates isolated scan workspaces."""

    def __call__(self, scan_id: UUID) -> ScanWorkspace: ...


@runtime_checkable
class IdempotencyCache(Protocol):
    """Idempotency key cache for scan create."""

    async def get(self, key: str) -> str | None: ...

    async def set(
        self, key: str, value: str, ttl_seconds: int | None = None
    ) -> None: ...


@runtime_checkable
class ModelCache(Protocol):
    """Hot cache for context models."""

    async def get(self, key: str) -> bytes | None: ...

    async def set(
        self, key: str, value: bytes, ttl_seconds: int | None = None
    ) -> None: ...

    async def delete(self, key: str) -> None: ...


@runtime_checkable
class OutboxWriter(Protocol):
    """Transactional outbox writer for domain events."""

    async def enqueue(self, event: EventEnvelope) -> None: ...


@runtime_checkable
class RateLimiter(Protocol):
    """Request rate limiter port."""

    async def allow(self, key: str, *, limit: int, window_seconds: int) -> bool: ...
