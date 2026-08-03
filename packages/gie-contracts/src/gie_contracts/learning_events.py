from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class LearningEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "learning-intelligence"
    producer_version: str

class FeedbackAccepted(LearningEventEnvelope):
    event_type: Literal["learning.feedback.accepted"] = "learning.feedback.accepted"
    feedback_id: str
    feedback_type: str

class LearningCycleCompleted(LearningEventEnvelope):
    event_type: Literal["learning.cycle.completed"] = "learning.cycle.completed"
    learning_id: UUID
    improved_count: int
    knowledge_proposed: int
    duration_ms: int

class KnowledgeChangeApproved(LearningEventEnvelope):
    event_type: Literal["learning.knowledge.approved"] = "learning.knowledge.approved"
    change_ids: list[str]
    actor: str
