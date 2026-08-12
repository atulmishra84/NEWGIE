from __future__ import annotations
import copy
from typing import Any
from uuid import UUID
from gie_contracts.integration import (
    AuditLogEntry,
    IntegrationConnection,
    SyncResult,
    WebhookEvent,
)
from integration_intelligence.domain.ports import (
    AuditRepository,
    CacheStore,
    ConnectionRepository,
    EventPublisher,
    SecretStore,
    SyncRepository,
    WebhookRepository,
)


class InMemoryConnectionRepository(ConnectionRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, IntegrationConnection] = {}
        self._by_tenant: dict[str, list[UUID]] = {}

    async def save(self, conn: IntegrationConnection) -> None:
        self._by_id[conn.connection_id] = conn
        ids = self._by_tenant.setdefault(conn.tenant_id, [])
        if conn.connection_id not in ids:
            ids.append(conn.connection_id)

    async def get(self, connection_id: UUID) -> IntegrationConnection | None:
        return self._by_id.get(connection_id)

    async def list(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> list[IntegrationConnection]:
        ids = self._by_tenant.get(tenant_id) or []
        items = [self._by_id[i] for i in ids if i in self._by_id]
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return items[offset : offset + limit]


class InMemoryWebhookRepository(WebhookRepository):
    def __init__(self) -> None:
        self._items: list[WebhookEvent] = []

    async def save(self, event: WebhookEvent) -> None:
        self._items.append(event)

    async def list(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> list[WebhookEvent]:
        items = [e for e in self._items if e.tenant_id == tenant_id]
        items.sort(key=lambda e: e.received_at, reverse=True)
        return items[offset : offset + limit]


class InMemoryAuditRepository(AuditRepository):
    def __init__(self) -> None:
        self._items: list[AuditLogEntry] = []

    async def save(self, entry: AuditLogEntry) -> None:
        self._items.append(entry)

    async def list(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> list[AuditLogEntry]:
        items = [e for e in self._items if e.tenant_id == tenant_id]
        items.sort(key=lambda e: e.occurred_at, reverse=True)
        return items[offset : offset + limit]


class InMemorySyncRepository(SyncRepository):
    def __init__(self) -> None:
        self._items: list[SyncResult] = []

    async def save(self, result: SyncResult) -> None:
        self._items.append(result)

    async def list(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[SyncResult]:
        items = [s for s in self._items if s.tenant_id == tenant_id]
        items.sort(key=lambda s: s.created_at, reverse=True)
        return items[offset : offset + limit]


class InMemorySecretStore(SecretStore):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    async def put(self, key: str, value: dict[str, Any]) -> None:
        self._data[key] = copy.deepcopy(value)

    async def get(self, key: str) -> dict[str, Any] | None:
        v = self._data.get(key)
        return copy.deepcopy(v) if v else None

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)


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
