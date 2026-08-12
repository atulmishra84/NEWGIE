from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PolicyGenEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "policy-generator"
    producer_version: str


class PolicyPackageGenerationCompleted(PolicyGenEventEnvelope):
    event_type: Literal["policygen.generation.completed"] = (
        "policygen.generation.completed"
    )
    agent_id: str
    package_id: UUID
    policy_count: int
    artifact_count: int
    duration_ms: int


class PolicyPackageValidationCompleted(PolicyGenEventEnvelope):
    event_type: Literal["policygen.validation.completed"] = (
        "policygen.validation.completed"
    )
    package_id: UUID | None = None
    status: str
    error_count: int
