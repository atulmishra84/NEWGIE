"""Orchestrator contracts — gie.orchestrator.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


ORCHESTRATOR_SCHEMA = "gie.orchestrator.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionMode(StrEnum):
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"
    BATCH = "batch"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    PARTIAL = "partial"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"
    WAITING_APPROVAL = "waiting_approval"
    CACHED = "cached"


class AgentId(StrEnum):
    CONTEXT = "context"
    KNOWLEDGE = "knowledge"
    RISK = "risk"
    COMPLIANCE = "compliance"
    POLICY = "policy"
    RECOMMENDATION = "recommendation"
    GENERATOR = "generator"
    VALIDATION = "validation"
    EXPLAINABILITY = "explainability"
    LEARNING = "learning"
    INTEGRATION = "integration"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class AgentEndpoint(BaseModel):
    agent_id: AgentId
    base_url: str
    version: str = "1.0.0"
    healthy: bool = True
    latency_ms_p95: float = 0.0


class StepDefinition(BaseModel):
    step_id: str
    agent_id: AgentId
    depends_on: list[str] = Field(default_factory=list)
    timeout_ms: int = 30_000
    retries: int = 2
    parallel_group: str | None = None
    optional: bool = False
    requires_approval: bool = False
    version: str | None = None  # version routing override


class WorkflowDefinition(BaseModel):
    workflow_id: str = "gie.analyze.default"
    name: str = "GIE Unified Analysis"
    steps: list[StepDefinition] = Field(default_factory=list)
    parallel_enabled: bool = True


class AnalyzeRequest(BaseModel):
    tenant_id: str
    source: dict[str, Any] = Field(default_factory=dict)  # repo/folder/zip refs
    mode: ExecutionMode = ExecutionMode.SYNC
    workflow_id: str = "gie.analyze.default"
    agent_versions: dict[str, str] = Field(default_factory=dict)  # version routing
    options: dict[str, Any] = Field(default_factory=dict)
    require_human_approval: bool = False
    approval_gates: list[str] = Field(default_factory=list)  # step_ids
    cache: bool = True
    timeout_ms: int | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowRequest(BaseModel):
    tenant_id: str
    workflow: WorkflowDefinition
    input: dict[str, Any] = Field(default_factory=dict)
    mode: ExecutionMode = ExecutionMode.ASYNC
    agent_versions: dict[str, str] = Field(default_factory=dict)
    require_human_approval: bool = False
    cache: bool = True
    timeout_ms: int | None = None
    correlation_id: str | None = None


class BatchAnalyzeRequest(BaseModel):
    tenant_id: str
    items: list[AnalyzeRequest]
    mode: ExecutionMode = ExecutionMode.BATCH
    max_concurrency: int = Field(default=5, ge=1, le=50)


class ApprovalDecision(BaseModel):
    execution_id: UUID
    step_id: str
    approved: bool
    actor: str = ""
    note: str | None = None


class StepExecution(BaseModel):
    step_id: str
    agent_id: AgentId
    status: StepStatus = StepStatus.PENDING
    attempt: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    retries: int = 0
    error: str | None = None
    cached: bool = False
    version: str = "1.0.0"
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    span_id: str = Field(default_factory=lambda: uuid4().hex[:16])


class TraceSpan(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    agent_id: AgentId | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int = 0
    status: str = "ok"
    attributes: dict[str, Any] = Field(default_factory=dict)


class ExecutionTrace(BaseModel):
    trace_id: str
    execution_id: UUID
    tenant_id: str
    spans: list[TraceSpan] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    llm_enhancement: dict[str, Any] | None = None


class UnifiedAnalysisResult(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    recommendation: dict[str, Any] = Field(default_factory=dict)
    generator: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    explainability: dict[str, Any] = Field(default_factory=dict)


class ExecutionRecord(BaseModel):
    execution_id: UUID = Field(default_factory=uuid4)
    schema_version: str = ORCHESTRATOR_SCHEMA
    tenant_id: str
    workflow_id: str
    mode: ExecutionMode
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    correlation_id: str = Field(default_factory=lambda: uuid4().hex)
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    steps: list[StepExecution] = Field(default_factory=list)
    result: UnifiedAnalysisResult | None = None
    error: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    events_published: int = 0
    cache_hits: int = 0
    agent_versions: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    stream_chunks: list[dict[str, Any]] = Field(default_factory=list)
    llm_enhancement: dict[str, Any] | None = None


class OrchestratorStatus(BaseModel):
    schema_version: str = ORCHESTRATOR_SCHEMA
    orchestrator: str = "orchestrator"
    version: str = "1.0.0"
    healthy: bool = True
    agents: list[AgentEndpoint] = Field(default_factory=list)
    active_executions: int = 0
    queued_executions: int = 0
    cache_size: int = 0
    uptime_hints: dict[str, Any] = Field(default_factory=dict)
