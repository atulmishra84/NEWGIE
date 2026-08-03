from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class ValidationEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "validation-intelligence"
    producer_version: str

class ValidationCompleted(ValidationEventEnvelope):
    event_type: Literal["validation.completed"] = "validation.completed"
    validation_id: UUID
    verdict: str
    approval_status: str
    finding_count: int
    duration_ms: int

class SimulationCompleted(ValidationEventEnvelope):
    event_type: Literal["validation.simulation.completed"] = "validation.simulation.completed"
    validation_id: UUID | None = None
    scenario_count: int
    failed_scenarios: int
