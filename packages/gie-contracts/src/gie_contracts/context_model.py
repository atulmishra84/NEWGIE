"""Normalized Context Model schema: gie.context.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


CONTEXT_MODEL_SCHEMA = "gie.context.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(BaseModel):
    """Detection confidence in [0, 1] with optional rationale."""

    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class EvidenceRef(BaseModel):
    evidence_id: str
    path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    detector_id: str
    excerpt_hash: str | None = None


class DetectedItem(BaseModel):
    name: str
    version: str | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class IdentitySection(BaseModel):
    languages: list[DetectedItem] = Field(default_factory=list)
    package_managers: list[DetectedItem] = Field(default_factory=list)
    runtimes: list[DetectedItem] = Field(default_factory=list)
    cloud_providers: list[DetectedItem] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    project_name: str | None = None
    repository_url: str | None = None


class AiSection(BaseModel):
    frameworks: list[DetectedItem] = Field(default_factory=list)
    sdks: list[DetectedItem] = Field(default_factory=list)
    models: list[DetectedItem] = Field(default_factory=list)
    prompts: list[DetectedItem] = Field(default_factory=list)
    memory_architectures: list[DetectedItem] = Field(default_factory=list)
    workflows: list[DetectedItem] = Field(default_factory=list)
    autonomous_capabilities: list[DetectedItem] = Field(default_factory=list)


class InterfacesSection(BaseModel):
    apis: list[DetectedItem] = Field(default_factory=list)
    tools: list[DetectedItem] = Field(default_factory=list)
    mcp_servers: list[DetectedItem] = Field(default_factory=list)
    webhooks: list[DetectedItem] = Field(default_factory=list)


class SecretFinding(BaseModel):
    """Redacted secret metadata — never includes raw secret values."""

    kind: str
    location: str
    fingerprint: str
    severity: Severity = Severity.HIGH
    confidence: Confidence = Field(default_factory=lambda: Confidence(score=0.9))
    evidence: list[EvidenceRef] = Field(default_factory=list)


class DataSection(BaseModel):
    vector_databases: list[DetectedItem] = Field(default_factory=list)
    data_stores: list[DetectedItem] = Field(default_factory=list)
    secret_findings: list[SecretFinding] = Field(default_factory=list)


class SecuritySection(BaseModel):
    identity_providers: list[DetectedItem] = Field(default_factory=list)
    auth_schemes: list[DetectedItem] = Field(default_factory=list)
    secret_managers: list[DetectedItem] = Field(default_factory=list)


class DeploymentSection(BaseModel):
    containers: list[DetectedItem] = Field(default_factory=list)
    kubernetes: list[DetectedItem] = Field(default_factory=list)
    cloud_resources: list[DetectedItem] = Field(default_factory=list)
    ide_workspaces: list[DetectedItem] = Field(default_factory=list)
    architecture_notes: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    kind: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSection(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class ReasoningStep(BaseModel):
    step: int
    detector_id: str
    action: str
    detail: str
    confidence: Confidence = Field(default_factory=Confidence)


class ProvenanceSection(BaseModel):
    schema_version: str = CONTEXT_MODEL_SCHEMA
    agent_name: str = "context-intelligence"
    agent_version: str
    scan_id: UUID
    tenant_id: str
    created_at: datetime = Field(default_factory=utcnow)
    detectors: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[ReasoningStep] = Field(default_factory=list)
    source_type: str
    source_digest: str | None = None


class ContextModel(BaseModel):
    """Normalized context consumed by downstream GIE agents."""

    model_id: UUID = Field(default_factory=uuid4)
    schema_version: str = CONTEXT_MODEL_SCHEMA
    version: int = 1
    identity: IdentitySection = Field(default_factory=IdentitySection)
    ai: AiSection = Field(default_factory=AiSection)
    interfaces: InterfacesSection = Field(default_factory=InterfacesSection)
    data: DataSection = Field(default_factory=DataSection)
    security: SecuritySection = Field(default_factory=SecuritySection)
    deployment: DeploymentSection = Field(default_factory=DeploymentSection)
    graph: GraphSection = Field(default_factory=GraphSection)
    provenance: ProvenanceSection

    def overall_confidence(self) -> float:
        return self.provenance.confidence.score
