from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class ExplainabilityEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "explainability-intelligence"
    producer_version: str

class ExplanationGenerated(ExplainabilityEventEnvelope):
    event_type: Literal["explainability.explanation.generated"] = "explainability.explanation.generated"
    explanation_id: UUID
    decision_id: str | None = None
    audience_count: int
    artifact_count: int
    duration_ms: int

class ReasoningPathBuilt(ExplainabilityEventEnvelope):
    event_type: Literal["explainability.reasoning_path.built"] = "explainability.reasoning_path.built"
    explanation_id: UUID | None = None
    step_count: int
