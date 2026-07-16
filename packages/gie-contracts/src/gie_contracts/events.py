"""Kafka / outbox event contracts for Context Intelligence Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from gie_contracts.sources import ScanSource


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    causation_id: str | None = None
    producer: str = "context-intelligence"
    producer_version: str


class ContextScanRequested(EventEnvelope):
    event_type: Literal["context.scan.requested"] = "context.scan.requested"
    scan_id: UUID
    source: ScanSource
    idempotency_key: str
    requested_by: str
    webhook_url: str | None = None


class ContextScanStarted(EventEnvelope):
    event_type: Literal["context.scan.started"] = "context.scan.started"
    scan_id: UUID


class ContextScanCompleted(EventEnvelope):
    event_type: Literal["context.scan.completed"] = "context.scan.completed"
    scan_id: UUID
    model_id: UUID
    model_version: int
    confidence: float
    duration_ms: int


class ContextScanFailed(EventEnvelope):
    event_type: Literal["context.scan.failed"] = "context.scan.failed"
    scan_id: UUID
    error_code: str
    error_message: str
    retryable: bool = True


class ContextModelUpdated(EventEnvelope):
    event_type: Literal["context.model.updated"] = "context.model.updated"
    model_id: UUID
    scan_id: UUID
    version: int
    schema_version: str
    summary: dict[str, Any] = Field(default_factory=dict)
