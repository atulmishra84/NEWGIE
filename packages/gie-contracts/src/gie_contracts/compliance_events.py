from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class ComplianceEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "compliance-intelligence"
    producer_version: str

class ComplianceAnalysisCompleted(ComplianceEventEnvelope):
    event_type: Literal["compliance.analysis.completed"] = "compliance.analysis.completed"
    application_id: str
    report_id: UUID
    compliance_score: float
    gap_count: int
    duration_ms: int

class ComplianceValidationCompleted(ComplianceEventEnvelope):
    event_type: Literal["compliance.validation.completed"] = "compliance.validation.completed"
    application_id: str
    validated_controls: int
    still_missing: int
