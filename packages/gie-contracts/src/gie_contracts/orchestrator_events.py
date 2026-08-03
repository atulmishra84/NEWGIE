from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class OrchestratorEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "orchestrator"
    producer_version: str

class ExecutionStarted(OrchestratorEventEnvelope):
    event_type: Literal["orchestrator.execution.started"] = "orchestrator.execution.started"
    execution_id: UUID
    workflow_id: str
    mode: str

class ExecutionCompleted(OrchestratorEventEnvelope):
    event_type: Literal["orchestrator.execution.completed"] = "orchestrator.execution.completed"
    execution_id: UUID
    status: str
    duration_ms: int

class StepCompleted(OrchestratorEventEnvelope):
    event_type: Literal["orchestrator.step.completed"] = "orchestrator.step.completed"
    execution_id: UUID
    step_id: str
    agent_id: str
    status: str
    duration_ms: int

class ApprovalRequested(OrchestratorEventEnvelope):
    event_type: Literal["orchestrator.approval.requested"] = "orchestrator.approval.requested"
    execution_id: UUID
    step_id: str
