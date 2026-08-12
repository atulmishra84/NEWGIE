from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.risk import RiskReport
from risk_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    RiskReportRepository,
)


class InMemoryRiskReportRepository(RiskReportRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, RiskReport] = {}
        self._by_agent: dict[tuple[str, str], list[UUID]] = {}

    async def save(self, report: RiskReport) -> None:
        self._by_id[report.report_id] = report
        key = (report.tenant_id, report.agent_id)
        self._by_agent.setdefault(key, []).append(report.report_id)

    async def get(self, report_id: UUID) -> RiskReport | None:
        return self._by_id.get(report_id)

    async def latest_for_agent(
        self, tenant_id: str, agent_id: str
    ) -> RiskReport | None:
        ids = self._by_agent.get((tenant_id, agent_id)) or []
        if not ids:
            return None
        return self._by_id.get(ids[-1])

    async def history(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RiskReport]:
        items = []
        for (t, a), ids in self._by_agent.items():
            if t != tenant_id:
                continue
            if agent_id and a != agent_id:
                continue
            for i in ids:
                items.append(self._by_id[i])
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[offset : offset + limit]


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

    async def publish(
        self, topic: str, event: dict[str, Any], key: str | None = None
    ) -> None:
        self.events.append({"topic": topic, "key": key, "event": event})
