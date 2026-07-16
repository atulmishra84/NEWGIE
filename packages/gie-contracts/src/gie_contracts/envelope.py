"""API response envelopes with observability metadata."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    trace_id: str
    request_id: str
    correlation_id: str
    execution_ms: float
    confidence: float | None = None
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    agent_version: str
    agent_name: str = "context-intelligence"


class ObservabilityEnvelope(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    meta: ResponseMeta
