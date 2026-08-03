from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.learning import FeedbackEvent, KnowledgeChange, LearningReport
from learning_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    FeedbackRepository,
    KnowledgeChangeRepository,
    LearningReportRepository,
)

class InMemoryFeedbackRepository(FeedbackRepository):
    def __init__(self) -> None:
        self._items: list[FeedbackEvent] = []

    async def save(self, event: FeedbackEvent) -> None:
        self._items.append(event)

    async def list(self, tenant_id: str, limit: int = 100, offset: int = 0) -> list[FeedbackEvent]:
        items = [e for e in self._items if e.tenant_id == tenant_id]
        items.sort(key=lambda e: e.occurred_at, reverse=True)
        return items[offset: offset + limit]

class InMemoryLearningReportRepository(LearningReportRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, LearningReport] = {}
        self._by_tenant: dict[str, list[UUID]] = {}
        self._by_agent: dict[tuple[str, str], list[UUID]] = {}

    async def save(self, report: LearningReport) -> None:
        self._by_id[report.learning_id] = report
        self._by_tenant.setdefault(report.tenant_id, []).append(report.learning_id)
        if report.agent_id:
            self._by_agent.setdefault((report.tenant_id, report.agent_id), []).append(report.learning_id)

    async def get(self, learning_id: UUID) -> LearningReport | None:
        return self._by_id.get(learning_id)

    async def history(self, tenant_id: str, agent_id: str | None = None, limit: int = 50, offset: int = 0) -> list[LearningReport]:
        if agent_id:
            ids = self._by_agent.get((tenant_id, agent_id)) or []
        else:
            ids = self._by_tenant.get(tenant_id) or []
        items = [self._by_id[i] for i in ids if i in self._by_id]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[offset: offset + limit]

class InMemoryKnowledgeChangeRepository(KnowledgeChangeRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, KnowledgeChange] = {}
        self._by_tenant: dict[str, list[UUID]] = {}

    async def save(self, change: KnowledgeChange) -> None:
        self._by_id[change.change_id] = change
        ids = self._by_tenant.setdefault(change.tenant_id, [])
        if change.change_id not in ids:
            ids.append(change.change_id)

    async def get(self, change_id: UUID) -> KnowledgeChange | None:
        return self._by_id.get(change_id)

    async def list(self, tenant_id: str, status: str | None = None, limit: int = 100, offset: int = 0) -> list[KnowledgeChange]:
        ids = self._by_tenant.get(tenant_id) or []
        items = [self._by_id[i] for i in ids if i in self._by_id]
        if status:
            items = [i for i in items if i.status.value == status]
        items.sort(key=lambda c: c.created_at, reverse=True)
        return items[offset: offset + limit]

    async def save_many(self, changes: list[KnowledgeChange]) -> None:
        for c in changes:
            await self.save(c)

class InMemoryCache(CacheStore):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
    async def get_json(self, key: str) -> dict[str, Any] | None:
        return copy.deepcopy(self._data.get(key))
    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None:
        self._data[key] = copy.deepcopy(value)

class LoggingEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
    async def publish(self, topic: str, event: dict[str, Any], key: str | None = None) -> None:
        self.events.append({"topic": topic, "key": key, "event": event})
