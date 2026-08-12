from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.validation import ValidationReport
from validation_intelligence.domain.ports import (
    CacheStore,
    EventPublisher,
    ValidationReportRepository,
)


class InMemoryValidationReportRepository(ValidationReportRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ValidationReport] = {}
        self._by_tenant: dict[str, list[UUID]] = {}
        self._by_agent: dict[tuple[str, str], list[UUID]] = {}

    async def save(self, report: ValidationReport) -> None:
        self._by_id[report.validation_id] = report
        self._by_tenant.setdefault(report.tenant_id, []).append(report.validation_id)
        if report.agent_id:
            self._by_agent.setdefault((report.tenant_id, report.agent_id), []).append(
                report.validation_id
            )

    async def get(self, validation_id: UUID) -> ValidationReport | None:
        return self._by_id.get(validation_id)

    async def latest(
        self, tenant_id: str, agent_id: str | None = None
    ) -> ValidationReport | None:
        if agent_id:
            ids = self._by_agent.get((tenant_id, agent_id)) or []
        else:
            ids = self._by_tenant.get(tenant_id) or []
        return self._by_id.get(ids[-1]) if ids else None

    async def list(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[ValidationReport]:
        ids = self._by_tenant.get(tenant_id) or []
        items = [self._by_id[i] for i in ids if i in self._by_id]
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
