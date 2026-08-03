from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Protocol
from uuid import UUID
from gie_contracts.policy import PolicyDecision, PolicyGenerateRequest, PolicyInputBundle

class DecisionRepository(ABC):
    @abstractmethod
    async def save(self, decision: PolicyDecision) -> None: ...
    @abstractmethod
    async def get(self, decision_id: UUID) -> PolicyDecision | None: ...
    @abstractmethod
    async def list(self, tenant_id: str, limit: int = 50, offset: int = 0) -> list[PolicyDecision]: ...

class CacheStore(ABC):
    @abstractmethod
    async def get_json(self, key: str) -> dict[str, Any] | None: ...
    @abstractmethod
    async def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None: ...

class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, topic: str, event: dict[str, Any], key: str | None = None) -> None: ...

class KnowledgeClient(Protocol):
    async def query(self, query: str, top_k: int = 5) -> dict[str, Any]: ...
