"""Policy Intelligence contracts — gie.policy.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


POLICY_SCHEMA = "gie.policy.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PolicyTarget(StrEnum):
    OPENAI = "openai"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    OPA_REGO = "opa_rego"
    NVIDIA_NEMO = "nvidia_nemo"
    PRESIDIO = "microsoft_presidio"


class OutputFormat(StrEnum):
    YAML = "yaml"
    JSON = "json"
    REGO = "rego"
    VENDOR_NATIVE = "vendor_native"


class Priority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Effort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BusinessImpact(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class ReasoningStep(BaseModel):
    step: int
    action: str
    detail: str
    inputs: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)


class PolicyInputBundle(BaseModel):
    """Inputs consumed by the Policy Intelligence Agent."""

    tenant_id: str
    context: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    identity: dict[str, Any] = Field(default_factory=dict)
    business: dict[str, Any] = Field(default_factory=dict)
    targets: list[PolicyTarget] = Field(default_factory=list)
    formats: list[OutputFormat] = Field(
        default_factory=lambda: [OutputFormat.YAML, OutputFormat.JSON, OutputFormat.REGO, OutputFormat.VENDOR_NATIVE]
    )


class GuardrailRecommendation(BaseModel):
    guardrail_id: str
    name: str
    category: str
    applies: bool = True
    why: list[str] = Field(default_factory=list)
    priority: Priority = Priority.P1
    confidence: Confidence = Field(default_factory=Confidence)
    business_impact: BusinessImpact = BusinessImpact.MEDIUM
    implementation_effort: Effort = Effort.MEDIUM
    knowledge_refs: list[str] = Field(default_factory=list)
    risk_refs: list[str] = Field(default_factory=list)
    compliance_refs: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)


class GeneratedArtifact(BaseModel):
    target: PolicyTarget
    format: OutputFormat
    filename: str
    content_type: str
    content: str
    checksum: str | None = None


class PolicyDecision(BaseModel):
    """Deployment-ready policy package with explainability."""

    decision_id: UUID = Field(default_factory=uuid4)
    schema_version: str = POLICY_SCHEMA
    tenant_id: str
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "policy-intelligence"
    agent_version: str = "1.0.0"
    recommendations: list[GuardrailRecommendation] = Field(default_factory=list)
    artifacts: list[GeneratedArtifact] = Field(default_factory=list)
    reasoning_path: list[ReasoningStep] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    summary: str = ""
    input_digest: str | None = None
    llm_enhancement: dict[str, Any] | None = None


class PolicyGenerateRequest(BaseModel):
    bundle: PolicyInputBundle
    idempotency_key: str | None = None
    dry_run: bool = False


class PolicyExplainRequest(BaseModel):
    decision_id: UUID
    guardrail_id: str | None = None
