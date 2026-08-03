"""Kafka events for Risk Intelligence Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RiskEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "risk-intelligence"
    producer_version: str


class RiskCalculationRequested(RiskEventEnvelope):
    event_type: Literal["risk.calculation.requested"] = "risk.calculation.requested"
    agent_id: str
    request_id: UUID


class RiskCalculationCompleted(RiskEventEnvelope):
    event_type: Literal["risk.calculation.completed"] = "risk.calculation.completed"
    agent_id: str
    report_id: UUID
    overall_ai_risk_score: float
    trust_score: float
    severity: str
    duration_ms: int


class RiskCalculationFailed(RiskEventEnvelope):
    event_type: Literal["risk.calculation.failed"] = "risk.calculation.failed"
    agent_id: str
    error_code: str
    error_message: str
    retryable: bool = True
