from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.policy_generator import PolicyPackage
from policy_generator.domain.ports import CacheStore, EventPublisher, PolicyPackageRepository

class InMemoryPolicyPackageRepository(PolicyPackageRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, PolicyPackage] = {}
        self._by_agent: dict[tuple[str, str], list[UUID]] = {}
        self._tenant: dict[str, list[UUID]] = {}

    async def save(self, package: PolicyPackage) -> None:
        self._by_id[package.package_id] = package
        self._by_agent.setdefault((package.tenant_id, package.agent_id), []).append(package.package_id)
        self._tenant.setdefault(package.tenant_id, []).append(package.package_id)

    async def get(self, package_id: UUID) -> PolicyPackage | None:
        return self._by_id.get(package_id)

    async def latest_for_agent(self, tenant_id: str, agent_id: str) -> PolicyPackage | None:
        ids = self._by_agent.get((tenant_id, agent_id)) or []
        return self._by_id.get(ids[-1]) if ids else None

    async def list(self, tenant_id: str, limit: int = 50, offset: int = 0) -> list[PolicyPackage]:
        ids = self._tenant.get(tenant_id) or []
        items = [self._by_id[i] for i in ids if i in self._by_id]
        items.sort(key=lambda p: p.created_at, reverse=True)
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
