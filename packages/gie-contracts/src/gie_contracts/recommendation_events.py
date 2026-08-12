from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RecommendationEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "recommendation-intelligence"
    producer_version: str


class RecommendationGenerated(RecommendationEventEnvelope):
    event_type: Literal["recommendation.generated"] = "recommendation.generated"
    agent_id: str
    report_id: UUID
    recommendation_count: int
    critical_count: int
    duration_ms: int


class RecommendationApproved(RecommendationEventEnvelope):
    event_type: Literal["recommendation.approved"] = "recommendation.approved"
    agent_id: str
    report_id: UUID
    approved_ids: list[str]
    actor: str
