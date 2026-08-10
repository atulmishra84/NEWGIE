"""Knowledge Intelligence contracts — versioned knowledge graph schema gie.knowledge.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


KNOWLEDGE_SCHEMA = "gie.knowledge.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeDomain(StrEnum):
    OWASP_LLM = "owasp_llm"
    MITRE_ATLAS = "mitre_atlas"
    NIST_AI_RMF = "nist_ai_rmf"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    EU_AI_ACT = "eu_ai_act"
    FINANCIAL = "financial_regulations"
    HEALTHCARE = "healthcare_regulations"
    IDENTITY_SECURITY = "identity_security"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    GUARDRAIL_TEMPLATES = "guardrail_templates"
    VENDOR_CAPABILITIES = "vendor_capabilities"
    RUNTIME_RESTRICTIONS = "runtime_restrictions"
    IDENTITY_POLICIES = "identity_policies"
    POLICY_MAPPINGS = "policy_mappings"


class NodeKind(StrEnum):
    FRAMEWORK = "Framework"
    CONTROL = "Control"
    THREAT = "Threat"
    TECHNIQUE = "Technique"
    ATTACK = "Attack"
    GUARDRAIL = "Guardrail"
    VENDOR = "Vendor"
    CAPABILITY = "Capability"
    POLICY = "Policy"
    RESTRICTION = "Restriction"
    MAPPING = "Mapping"
    EVIDENCE = "Evidence"
    CONCEPT = "Concept"


class RelationType(StrEnum):
    MAPS_TO = "MAPS_TO"
    MITIGATES = "MITIGATES"
    EXPLOITS = "EXPLOITS"
    REQUIRES = "REQUIRES"
    IMPLEMENTS = "IMPLEMENTS"
    RELATED_TO = "RELATED_TO"
    SUPERSEDES = "SUPERSEDES"
    EVIDENCED_BY = "EVIDENCED_BY"
    OWNS = "OWNS"
    CONSTRAINS = "CONSTRAINS"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class EvidenceRef(BaseModel):
    evidence_id: str = Field(default_factory=lambda: uuid4().hex)
    source_uri: str | None = None
    source_title: str | None = None
    citation: str | None = None
    retrieved_at: datetime | None = None
    content_hash: str | None = None
    excerpt: str | None = None


class KnowledgeNode(BaseModel):
    node_id: str
    kind: NodeKind
    domain: KnowledgeDomain
    title: str
    summary: str = ""
    body: str = ""
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    version: str = "1.0.0"
    schema_version: str = KNOWLEDGE_SCHEMA
    confidence: Confidence = Field(default_factory=Confidence)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    superseded_by: str | None = None
    active: bool = True


class KnowledgeEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: uuid4().hex)
    source_id: str
    target_id: str
    relationship: RelationType
    weight: float = Field(ge=0.0, le=1.0, default=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    version: str = "1.0.0"
    confidence: Confidence = Field(default_factory=Confidence)
    created_at: datetime = Field(default_factory=utcnow)


class ReasoningStep(BaseModel):
    step: int
    action: str
    detail: str
    node_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)


class RetrievalHit(BaseModel):
    node: KnowledgeNode
    score: float
    rank: int
    match_type: str  # semantic | keyword | graph | hybrid
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ExplainableRetrievalResult(BaseModel):
    """Semantic/hybrid retrieval with evidence and reasoning path."""

    query_id: UUID = Field(default_factory=uuid4)
    query: str
    hits: list[RetrievalHit] = Field(default_factory=list)
    reasoning_path: list[ReasoningStep] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    graph_paths: list[list[str]] = Field(default_factory=list)
    version_pin: str | None = None
    took_ms: float = 0.0
    agent_version: str = "1.0.0"
    schema_version: str = KNOWLEDGE_SCHEMA
    llm_enhancement: dict[str, Any] | None = None


class KnowledgeGraphSnapshot(BaseModel):
    snapshot_id: UUID = Field(default_factory=uuid4)
    version: str
    schema_version: str = KNOWLEDGE_SCHEMA
    node_count: int = 0
    edge_count: int = 0
    domains: list[KnowledgeDomain] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    checksum: str | None = None


class KnowledgeUpsertRequest(BaseModel):
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    idempotency_key: str | None = None
    publish_version: bool = False
    version_label: str | None = None


class KnowledgeQueryRequest(BaseModel):
    query: str
    domains: list[KnowledgeDomain] = Field(default_factory=list)
    kinds: list[NodeKind] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=100)
    version: str | None = None
    include_graph: bool = True
    include_evidence: bool = True
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    hybrid: bool = True


class KnowledgeDiff(BaseModel):
    from_version: str
    to_version: str
    added_nodes: list[str] = Field(default_factory=list)
    removed_nodes: list[str] = Field(default_factory=list)
    changed_nodes: list[str] = Field(default_factory=list)
    added_edges: list[str] = Field(default_factory=list)
    removed_edges: list[str] = Field(default_factory=list)
