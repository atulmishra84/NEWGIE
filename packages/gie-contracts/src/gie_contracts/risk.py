"""Risk Intelligence contracts — gie.risk.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


RISK_SCHEMA = "gie.risk.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RiskCategory(StrEnum):
    SECURITY = "security"
    PRIVACY = "privacy"
    COMPLIANCE = "compliance"
    IDENTITY = "identity"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    HALLUCINATION = "hallucination"
    SUPPLY_CHAIN = "supply_chain"
    MODEL = "model"
    TOOL_ABUSE = "tool_abuse"
    DATA_LEAKAGE = "data_leakage"
    SHADOW_AI = "shadow_ai"
    RUNTIME = "runtime"
    AUTONOMY = "autonomy"
    BUSINESS = "business"
    OPERATIONAL = "operational"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class FrameworkMapping(BaseModel):
    framework: str  # mitre_atlas | owasp_llm | nist_ai_rmf
    ids: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)


class RemediationAction(BaseModel):
    action_id: str
    title: str
    description: str
    priority: str = "P1"
    effort: str = "medium"
    related_guardrails: list[str] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)


class RiskFactor(BaseModel):
    factor_id: str
    category: RiskCategory
    name: str
    score: float = Field(ge=0.0, le=1.0)
    severity: Severity
    explanation: str
    evidence: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    mappings: list[FrameworkMapping] = Field(default_factory=list)
    remediations: list[RemediationAction] = Field(default_factory=list)
    weight: float = Field(ge=0.0, le=1.0, default=1.0)


class ReasoningStep(BaseModel):
    step: int
    action: str
    detail: str
    category: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)


class RiskInputBundle(BaseModel):
    """Inputs consumed by the Risk Intelligence Agent."""

    tenant_id: str
    agent_id: str
    context_model: dict[str, Any] = Field(default_factory=dict)
    knowledge_graph: dict[str, Any] = Field(default_factory=dict)
    compliance_requirements: dict[str, Any] = Field(default_factory=dict)
    identity_metadata: dict[str, Any] = Field(default_factory=dict)
    runtime_configuration: dict[str, Any] = Field(default_factory=dict)
    ai_models: list[dict[str, Any]] = Field(default_factory=list)
    prompt_analysis: dict[str, Any] = Field(default_factory=dict)
    tool_permissions: dict[str, Any] = Field(default_factory=dict)
    agent_capabilities: dict[str, Any] = Field(default_factory=dict)
    org_risk_model: dict[str, Any] | None = None  # custom weights / thresholds


class HeatmapCell(BaseModel):
    category: RiskCategory
    score: float
    severity: Severity
    x: int
    y: int


class RiskGraphNode(BaseModel):
    id: str
    kind: str
    label: str
    score: float | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class RiskGraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class RiskTimelineEvent(BaseModel):
    at: datetime
    event: str
    overall_score: float
    trust_score: float
    decision_id: UUID | None = None


class RiskReport(BaseModel):
    """Full risk posture report."""

    report_id: UUID = Field(default_factory=uuid4)
    schema_version: str = RISK_SCHEMA
    tenant_id: str
    agent_id: str
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "risk-intelligence"
    agent_version: str = "1.0.0"
    factors: list[RiskFactor] = Field(default_factory=list)
    category_scores: dict[str, float] = Field(default_factory=dict)
    overall_ai_risk_score: float = Field(ge=0.0, le=1.0, default=0.0)
    trust_score: float = Field(ge=0.0, le=1.0, default=0.0)
    severity: Severity = Severity.MEDIUM
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[ReasoningStep] = Field(default_factory=list)
    remediations: list[RemediationAction] = Field(default_factory=list)
    mappings_summary: dict[str, list[str]] = Field(default_factory=dict)
    heatmap: list[HeatmapCell] = Field(default_factory=list)
    risk_graph: dict[str, Any] = Field(default_factory=dict)
    timeline: list[RiskTimelineEvent] = Field(default_factory=list)
    input_digest: str | None = None
    model_id: str = "default-v1"


class RiskCalculateRequest(BaseModel):
    bundle: RiskInputBundle
    idempotency_key: str | None = None
    persist: bool = True


class RiskRecalculateRequest(BaseModel):
    agent_id: str
    tenant_id: str
    bundle: RiskInputBundle | None = None
    org_risk_model: dict[str, Any] | None = None
