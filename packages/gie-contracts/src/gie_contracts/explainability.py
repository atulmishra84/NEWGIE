"""Explainability Intelligence contracts — gie.explainability.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


EXPLAINABILITY_SCHEMA = "gie.explainability.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AudienceView(StrEnum):
    EXECUTIVE = "executive"
    DEVELOPER = "developer"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    AUDITOR = "auditor"


class OutputFormat(StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class AlternativeOption(BaseModel):
    option_id: str = Field(default_factory=lambda: uuid4().hex[:10])
    title: str
    description: str
    tradeoffs: str = ""
    estimated_risk_delta: float | None = None


class ExplanationDimensions(BaseModel):
    why: str
    evidence: list[str] = Field(default_factory=list)
    risk: str = ""
    regulation: str = ""
    business_impact: str = ""
    confidence: Confidence = Field(default_factory=Confidence)
    alternative_options: list[AlternativeOption] = Field(default_factory=list)
    expected_outcome: str = ""
    supporting_knowledge: list[str] = Field(default_factory=list)
    policy_source: str = ""


class AudienceExplanation(BaseModel):
    audience: AudienceView
    title: str
    summary: str
    narrative: str
    dimensions: ExplanationDimensions
    emphasis: list[str] = Field(default_factory=list)


class RenderedArtifact(BaseModel):
    format: OutputFormat
    filename: str
    content_type: str
    content: str
    encoding: str = "utf-8"


class ReasoningStep(BaseModel):
    step: int
    agent: str
    action: str
    detail: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)


class ExplainabilityInputBundle(BaseModel):
    tenant_id: str
    decision_id: str | None = None
    agent_id: str | None = None
    subject_type: str = "recommendation"  # recommendation | risk | compliance | policy | decision
    subject: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    risk: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)
    policy_package: dict[str, Any] = Field(default_factory=dict)
    identity: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    formats: list[OutputFormat] = Field(default_factory=list)
    audiences: list[AudienceView] = Field(default_factory=list)


class ExplanationReport(BaseModel):
    explanation_id: UUID = Field(default_factory=uuid4)
    schema_version: str = EXPLAINABILITY_SCHEMA
    tenant_id: str
    agent_id: str | None = None
    decision_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "explainability-intelligence"
    agent_version: str = "1.0.0"
    subject_type: str = "recommendation"
    dimensions: ExplanationDimensions
    views: dict[str, AudienceExplanation] = Field(default_factory=dict)
    reasoning_path: list[ReasoningStep] = Field(default_factory=list)
    artifacts: list[RenderedArtifact] = Field(default_factory=list)
    mermaid_diagram: str = ""
    figma_diagram: dict[str, Any] = Field(default_factory=dict)
    confidence: Confidence = Field(default_factory=Confidence)
    summary: str = ""


class ExplainRequest(BaseModel):
    bundle: ExplainabilityInputBundle
    persist: bool = True


class ReasoningPathRequest(BaseModel):
    tenant_id: str
    agent_id: str | None = None
    decision_id: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    risk: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    knowledge: dict[str, Any] = Field(default_factory=dict)
