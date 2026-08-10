from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.compliance import ComplianceReport
from compliance_intelligence.domain.ports import (
    CacheStore,
    ComplianceReportRepository,
    EventPublisher,
)


class InMemoryComplianceReportRepository(ComplianceReportRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ComplianceReport] = {}
        self._by_app: dict[tuple[str, str], list[UUID]] = {}

    async def save(self, report: ComplianceReport) -> None:
        self._by_id[report.report_id] = report
        self._by_app.setdefault((report.tenant_id, report.application_id), []).append(
            report.report_id
        )

    async def get(self, report_id: UUID) -> ComplianceReport | None:
        return self._by_id.get(report_id)

    async def latest(
        self, tenant_id: str, application_id: str
    ) -> ComplianceReport | None:
        ids = self._by_app.get((tenant_id, application_id)) or []
        return self._by_id.get(ids[-1]) if ids else None

    async def list(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[ComplianceReport]:
        items = [
            self._by_id[i]
            for (t, _), ids in self._by_app.items()
            if t == tenant_id
            for i in ids
        ]
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
