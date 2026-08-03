"""Compliance Intelligence contracts — gie.compliance.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


COMPLIANCE_SCHEMA = "gie.compliance.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FrameworkId(StrEnum):
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    NIST_AI_RMF = "nist_ai_rmf"
    NIST_CSF = "nist_csf"
    EU_AI_ACT = "eu_ai_act"
    FDA = "fda"
    RBI = "rbi"
    MAS = "mas"
    DORA = "dora"
    CCPA = "ccpa"
    INTERNAL = "internal_corporate"


class ControlStatus(StrEnum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class GapSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: uuid4().hex)
    control_id: str
    title: str
    description: str
    source: str | None = None
    artifact_uri: str | None = None
    collected_at: datetime = Field(default_factory=utcnow)
    checksum: str | None = None


class ControlRequirement(BaseModel):
    control_id: str
    framework: FrameworkId
    title: str
    description: str
    category: str = "general"
    version: str = "1.0.0"


class ControlAssessment(BaseModel):
    control_id: str
    framework: FrameworkId
    title: str
    status: ControlStatus
    gap_severity: GapSeverity | None = None
    gap_description: str | None = None
    recommended_controls: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    mapping_refs: list[str] = Field(default_factory=list)


class FrameworkApplicability(BaseModel):
    framework: FrameworkId
    applicable: bool
    confidence: Confidence = Field(default_factory=Confidence)
    reasons: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    last_regulatory_update: str | None = None


class ComplianceGap(BaseModel):
    gap_id: str
    framework: FrameworkId
    control_id: str
    title: str
    severity: GapSeverity
    description: str
    recommended_controls: list[str] = Field(default_factory=list)


class ComplianceMatrixRow(BaseModel):
    framework: FrameworkId
    control_id: str
    title: str
    status: ControlStatus
    evidence_count: int = 0
    gap_severity: GapSeverity | None = None


class ComplianceInputBundle(BaseModel):
    tenant_id: str
    application_id: str
    context_model: dict[str, Any] = Field(default_factory=dict)
    risk_report: dict[str, Any] = Field(default_factory=dict)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    identity: dict[str, Any] = Field(default_factory=dict)
    business: dict[str, Any] = Field(default_factory=dict)
    declared_frameworks: list[FrameworkId] = Field(default_factory=list)
    implemented_controls: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    internal_policies: list[dict[str, Any]] = Field(default_factory=list)
    policy_version: str | None = None


class ComplianceReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    schema_version: str = COMPLIANCE_SCHEMA
    tenant_id: str
    application_id: str
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "compliance-intelligence"
    agent_version: str = "1.0.0"
    applicable_frameworks: list[FrameworkApplicability] = Field(default_factory=list)
    assessments: list[ControlAssessment] = Field(default_factory=list)
    gaps: list[ComplianceGap] = Field(default_factory=list)
    matrix: list[ComplianceMatrixRow] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    compliance_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence: Confidence = Field(default_factory=Confidence)
    policy_version: str = "1.0.0"
    audit_package: dict[str, Any] = Field(default_factory=dict)
    control_mappings: dict[str, list[str]] = Field(default_factory=dict)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class ComplianceAnalyzeRequest(BaseModel):
    bundle: ComplianceInputBundle
    persist: bool = True


class ComplianceValidateRequest(BaseModel):
    tenant_id: str
    application_id: str
    control_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    implemented_controls: list[str] = Field(default_factory=list)
