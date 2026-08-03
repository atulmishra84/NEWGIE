from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.policy import PolicyDecision
from policy_intelligence.domain.ports import CacheStore, DecisionRepository, EventPublisher

class InMemoryDecisionRepository(DecisionRepository):
    def __init__(self) -> None:
        self._items: dict[UUID, PolicyDecision] = {}

    async def save(self, decision: PolicyDecision) -> None:
        self._items[decision.decision_id] = decision

    async def get(self, decision_id: UUID) -> PolicyDecision | None:
        return self._items.get(decision_id)

    async def list(self, tenant_id: str, limit: int = 50, offset: int = 0) -> list[PolicyDecision]:
        items = [d for d in self._items.values() if d.tenant_id == tenant_id]
        items.sort(key=lambda d: d.created_at, reverse=True)
        return items[offset: offset + limit]

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
