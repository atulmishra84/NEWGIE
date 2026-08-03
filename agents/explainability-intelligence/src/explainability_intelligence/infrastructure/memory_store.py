from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.explainability import ExplanationReport
from explainability_intelligence.domain.ports import CacheStore, EventPublisher, ExplanationRepository

class InMemoryExplanationRepository(ExplanationRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, ExplanationReport] = {}
        self._by_decision: dict[tuple[str, str], UUID] = {}

    async def save(self, report: ExplanationReport) -> None:
        self._by_id[report.explanation_id] = report
        if report.decision_id:
            self._by_decision[(report.tenant_id, report.decision_id)] = report.explanation_id

    async def get(self, explanation_id: UUID) -> ExplanationReport | None:
        return self._by_id.get(explanation_id)

    async def latest_for_decision(self, tenant_id: str, decision_id: str) -> ExplanationReport | None:
        eid = self._by_decision.get((tenant_id, decision_id))
        return self._by_id.get(eid) if eid else None

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
