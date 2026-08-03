from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID
from gie_contracts.recommendation import RecommendationReport

class RecommendationReportRepository(ABC):
    @abstractmethod
    async def save(self, report: RecommendationReport) -> None: ...
    @abstractmethod
    async def get(self, report_id: UUID) -> RecommendationReport | None: ...
    @abstractmethod
    async def latest_for_agent(self, tenant_id: str, agent_id: str) -> RecommendationReport | None: ...
    @abstractmethod
    async def history(self, tenant_id: str, agent_id: str | None = None, limit: int = 50, offset: int = 0) -> list[RecommendationReport]: ...

class CacheStore(ABC):
    @abstractmethod
    async def get_json(self, key: str) -> dict[str, Any] | None: ...
    @abstractmethod
    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None: ...

class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, topic: str, event: dict[str, Any], key: str | None = None) -> None: ...
