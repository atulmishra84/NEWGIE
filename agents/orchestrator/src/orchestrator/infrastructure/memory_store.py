from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.orchestrator import ExecutionRecord, ExecutionStatus, ExecutionTrace
from orchestrator.domain.ports import CacheStore, EventPublisher, ExecutionRepository, TraceRepository

class InMemoryExecutionRepository(ExecutionRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ExecutionRecord] = {}
        self._by_tenant: dict[str, list[UUID]] = {}

    async def save(self, record: ExecutionRecord) -> None:
        self._by_id[record.execution_id] = record
        ids = self._by_tenant.setdefault(record.tenant_id, [])
        if record.execution_id not in ids:
            ids.append(record.execution_id)

    async def get(self, execution_id: UUID) -> ExecutionRecord | None:
        return self._by_id.get(execution_id)

    async def list(self, tenant_id: str, limit: int = 50, offset: int = 0) -> list[ExecutionRecord]:
        ids = self._by_tenant.get(tenant_id) or []
        items = [self._by_id[i] for i in ids if i in self._by_id]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[offset: offset + limit]

    async def count_active(self) -> int:
        return sum(1 for r in self._by_id.values() if r.status in {ExecutionStatus.RUNNING, ExecutionStatus.PENDING, ExecutionStatus.WAITING_APPROVAL})

class InMemoryTraceRepository(TraceRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, ExecutionTrace] = {}

    async def save(self, trace: ExecutionTrace) -> None:
        self._by_id[trace.trace_id] = trace

    async def get(self, trace_id: str) -> ExecutionTrace | None:
        return self._by_id.get(trace_id)

class InMemoryCache(CacheStore):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    async def get_json(self, key: str) -> dict[str, Any] | None:
        return copy.deepcopy(self._data.get(key))

    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None:
        self._data[key] = copy.deepcopy(value)

    async def size(self) -> int:
        return len(self._data)

class LoggingEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish(self, topic: str, event: dict[str, Any], key: str | None = None) -> None:
        self.events.append({"topic": topic, "key": key, "event": event})
