from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID
from gie_contracts.compliance import ComplianceReport


class ComplianceReportRepository(ABC):
    @abstractmethod
    async def save(self, report: ComplianceReport) -> None: ...
    @abstractmethod
    async def get(self, report_id: UUID) -> ComplianceReport | None: ...
    @abstractmethod
    async def latest(
        self, tenant_id: str, application_id: str
    ) -> ComplianceReport | None: ...
    @abstractmethod
    async def list(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> list[ComplianceReport]: ...


class CacheStore(ABC):
    @abstractmethod
    async def get_json(self, key: str) -> dict[str, Any] | None: ...
    @abstractmethod
    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None: ...


class EventPublisher(ABC):
    @abstractmethod
    async def publish(
        self, topic: str, event: dict[str, Any], key: str | None = None
    ) -> None: ...
