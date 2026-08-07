"""Policy Generator contracts — gie.policygen.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


POLICYGEN_SCHEMA = "gie.policygen.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PolicyFormat(StrEnum):
    OPENAI_GUARDRAILS = "openai_guardrails"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    SEMANTIC_KERNEL = "semantic_kernel"
    NVIDIA_NEMO = "nvidia_nemo"
    OPA_REGO = "opa_rego"
    YAML = "yaml"
    JSON = "json"
    TERRAFORM = "terraform"
    KUBERNETES = "kubernetes"
    ADMISSION_CONTROLLER = "admission_controller"
    API_GATEWAY = "api_gateway"
    PROMPT = "prompt"
    IDENTITY = "identity"
    RUNTIME = "runtime"
    DLP = "dlp"


class ValidationStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class PolicyMetadata(BaseModel):
    policy_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    name: str
    description: str = ""
    version: str = "1.0.0"
    source: str = "recommendation-intelligence"
    created_at: datetime = Field(default_factory=utcnow)
    tenant_id: str | None = None
    agent_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class ComplianceMapping(BaseModel):
    frameworks: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    notes: str | None = None


class RiskMapping(BaseModel):
    categories: list[str] = Field(default_factory=list)
    severities: list[str] = Field(default_factory=list)
    recommendation_ids: list[str] = Field(default_factory=list)
    risk_reduction: float | None = Field(default=None, ge=0.0, le=1.0)


class ValidationResult(BaseModel):
    status: ValidationStatus = ValidationStatus.PENDING
    checked_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)


class RollbackPlan(BaseModel):
    strategy: str = "replace_previous_version"
    previous_version: str | None = None
    steps: list[str] = Field(default_factory=list)
    safe_to_auto_rollback: bool = True


class GeneratedPolicyArtifact(BaseModel):
    filename: str
    format: PolicyFormat
    content_type: str
    content: str
    checksum: str | None = None


class GeneratedPolicy(BaseModel):
    """A single deployment-ready policy package for one format/target."""

    metadata: PolicyMetadata
    format: PolicyFormat
    body: dict[str, Any] = Field(default_factory=dict)
    content: str = ""
    filename: str
    content_type: str = "application/json"
    compliance_mapping: ComplianceMapping = Field(default_factory=ComplianceMapping)
    risk_mapping: RiskMapping = Field(default_factory=RiskMapping)
    validation: ValidationResult = Field(default_factory=ValidationResult)
    rollback: RollbackPlan = Field(default_factory=RollbackPlan)
    artifact: GeneratedPolicyArtifact | None = None


class PolicyGeneratorInputBundle(BaseModel):
    tenant_id: str
    agent_id: str
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    risk: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)
    identity: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    formats: list[PolicyFormat] = Field(default_factory=list)
    policy_version: str = "1.0.0"
    source: str = "recommendation-intelligence"


class PolicyPackage(BaseModel):
    package_id: UUID = Field(default_factory=uuid4)
    schema_version: str = POLICYGEN_SCHEMA
    tenant_id: str
    agent_id: str
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "policy-generator"
    agent_version: str = "1.0.0"
    version: str = "1.0.0"
    source: str = "recommendation-intelligence"
    policies: list[GeneratedPolicy] = Field(default_factory=list)
    artifacts: list[GeneratedPolicyArtifact] = Field(default_factory=list)
    # Convenience named artifacts
    named_artifacts: dict[str, str] = Field(default_factory=dict)
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    validation: ValidationResult = Field(default_factory=ValidationResult)
    rollback: RollbackPlan = Field(default_factory=RollbackPlan)
    llm_enhancement: dict[str, Any] | None = None



class PolicyPackageGenerateRequest(BaseModel):
    bundle: PolicyGeneratorInputBundle
    persist: bool = True


class PolicyPackageValidateRequest(BaseModel):
    package_id: UUID | None = None
    content: str | None = None
    format: PolicyFormat | None = None
    filename: str | None = None
    policy: dict[str, Any] | None = None


class PolicyTemplate(BaseModel):
    template_id: str
    name: str
    format: PolicyFormat
    description: str
    version: str = "1.0.0"
    filename: str
    tags: list[str] = Field(default_factory=list)
