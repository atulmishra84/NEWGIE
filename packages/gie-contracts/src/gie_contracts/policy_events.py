"""Kafka events for Policy Intelligence Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PolicyEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "policy-intelligence"
    producer_version: str


class PolicyGenerationRequested(PolicyEventEnvelope):
    event_type: Literal["policy.generation.requested"] = "policy.generation.requested"
    request_id: UUID
    targets: list[str] = Field(default_factory=list)


class PolicyGenerationCompleted(PolicyEventEnvelope):
    event_type: Literal["policy.generation.completed"] = "policy.generation.completed"
    decision_id: UUID
    artifact_count: int
    recommendation_count: int
    confidence: float
    duration_ms: int


class PolicyGenerationFailed(PolicyEventEnvelope):
    event_type: Literal["policy.generation.failed"] = "policy.generation.failed"
    request_id: UUID
    error_code: str
    error_message: str
    retryable: bool = True
