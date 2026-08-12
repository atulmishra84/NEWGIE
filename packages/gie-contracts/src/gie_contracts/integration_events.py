from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IntegrationEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=utcnow)
    tenant_id: str
    correlation_id: str
    producer: str = "integration-intelligence"
    producer_version: str


class IntegrationConnected(IntegrationEventEnvelope):
    event_type: Literal["integration.connected"] = "integration.connected"
    connection_id: UUID
    platform_id: str
    auth_method: str


class IntegrationSyncCompleted(IntegrationEventEnvelope):
    event_type: Literal["integration.sync.completed"] = "integration.sync.completed"
    sync_id: UUID
    connection_id: UUID
    status: str


class WebhookReceived(IntegrationEventEnvelope):
    event_type: Literal["integration.webhook.received"] = "integration.webhook.received"
    event_id_ref: UUID
    platform_id: str
    event_type_name: str


class CircuitBreakerOpened(IntegrationEventEnvelope):
    event_type: Literal["integration.circuit.opened"] = "integration.circuit.opened"
    connection_id: UUID
    platform_id: str
    failure_count: int
