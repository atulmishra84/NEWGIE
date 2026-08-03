from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID
from gie_contracts.validation import ValidationReport

class ValidationReportRepository(ABC):
    @abstractmethod
    async def save(self, report: ValidationReport) -> None: ...
    @abstractmethod
    async def get(self, validation_id: UUID) -> ValidationReport | None: ...
    @abstractmethod
    async def latest(self, tenant_id: str, agent_id: str | None = None) -> ValidationReport | None: ...
    @abstractmethod
    async def list(self, tenant_id: str, limit: int = 50, offset: int = 0) -> list[ValidationReport]: ...

class CacheStore(ABC):
    @abstractmethod
    async def get_json(self, key: str) -> dict[str, Any] | None: ...
    @abstractmethod
    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None: ...

class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, topic: str, event: dict[str, Any], key: str | None = None) -> None: ...
