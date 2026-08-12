from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID
from gie_contracts.explainability import ExplanationReport


class ExplanationRepository(ABC):
    @abstractmethod
    async def save(self, report: ExplanationReport) -> None: ...
    @abstractmethod
    async def get(self, explanation_id: UUID) -> ExplanationReport | None: ...
    @abstractmethod
    async def latest_for_decision(
        self, tenant_id: str, decision_id: str
    ) -> ExplanationReport | None: ...


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
