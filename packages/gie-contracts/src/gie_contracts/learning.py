"""Learning Intelligence contracts — gie.learning.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


LEARNING_SCHEMA = "gie.learning.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeedbackType(StrEnum):
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    USER_FEEDBACK = "user_feedback"
    RUNTIME_TELEMETRY = "runtime_telemetry"
    SECURITY_INCIDENT = "security_incident"
    THREAT_INTELLIGENCE = "threat_intelligence"
    REGULATORY_UPDATE = "regulatory_update"
    POLICY_CHANGE = "policy_change"
    MODEL_CHANGE = "model_change"


class KnowledgeChangeStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class DriftSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None
    previous_score: float | None = Field(default=None, ge=0.0, le=1.0)
    delta: float | None = None


class FeedbackEvent(BaseModel):
    feedback_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    tenant_id: str
    agent_id: str | None = None
    feedback_type: FeedbackType
    title: str
    description: str = ""
    severity: str = "medium"
    recommendation_id: str | None = None
    policy_id: str | None = None
    signals: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    occurred_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImprovedRecommendation(BaseModel):
    recommendation_id: str
    title: str
    reason: str
    previous_confidence: float | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    priority: str = "medium"
    category: str = "security"
    changes: list[str] = Field(default_factory=list)
    related_feedback_ids: list[str] = Field(default_factory=list)


class PolicyUpdateRecommendation(BaseModel):
    update_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str
    description: str
    target_policy: str | None = None
    rationale: str
    severity: DriftSeverity = DriftSeverity.MEDIUM
    suggested_diff: dict[str, Any] = Field(default_factory=dict)


class DriftFinding(BaseModel):
    drift_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    kind: str  # policy_drift | regulation_change | new_attack_technique
    title: str
    detail: str
    severity: DriftSeverity = DriftSeverity.MEDIUM
    evidence: list[str] = Field(default_factory=list)


class KnowledgeChange(BaseModel):
    change_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    title: str
    description: str
    change_type: str  # recommendation | attack_technique | regulation | policy_rule
    payload: dict[str, Any] = Field(default_factory=dict)
    status: KnowledgeChangeStatus = KnowledgeChangeStatus.PROPOSED
    requires_human_approval: bool = True
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    source_feedback_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)


class LearningInputBundle(BaseModel):
    tenant_id: str
    agent_id: str | None = None
    feedback: list[FeedbackEvent] = Field(default_factory=list)
    runtime_telemetry: list[dict[str, Any]] = Field(default_factory=list)
    security_incidents: list[dict[str, Any]] = Field(default_factory=list)
    false_positives: list[dict[str, Any]] = Field(default_factory=list)
    false_negatives: list[dict[str, Any]] = Field(default_factory=list)
    user_feedback: list[dict[str, Any]] = Field(default_factory=list)
    threat_intelligence: list[dict[str, Any]] = Field(default_factory=list)
    regulatory_updates: list[dict[str, Any]] = Field(default_factory=list)
    policy_changes: list[dict[str, Any]] = Field(default_factory=list)
    model_changes: list[dict[str, Any]] = Field(default_factory=list)
    current_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    current_policies: dict[str, Any] = Field(default_factory=dict)
    knowledge_snapshot: dict[str, Any] = Field(default_factory=dict)
    auto_propose_knowledge: bool = True
    publish_without_approval: bool = False  # must stay false in prod paths


class LearningReport(BaseModel):
    learning_id: UUID = Field(default_factory=uuid4)
    schema_version: str = LEARNING_SCHEMA
    tenant_id: str
    agent_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "learning-intelligence"
    agent_version: str = "1.0.0"
    improved_recommendations: list[ImprovedRecommendation] = Field(default_factory=list)
    policy_updates: list[PolicyUpdateRecommendation] = Field(default_factory=list)
    drift_findings: list[DriftFinding] = Field(default_factory=list)
    knowledge_changes: list[KnowledgeChange] = Field(default_factory=list)
    confidence_improvements: list[dict[str, Any]] = Field(default_factory=list)
    feedback_consumed: int = 0
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    counts: dict[str, int] = Field(default_factory=dict)
    llm_enhancement: dict[str, Any] | None = None


class FeedbackRequest(BaseModel):
    event: FeedbackEvent
    persist: bool = True


class LearnRequest(BaseModel):
    bundle: LearningInputBundle
    persist: bool = True


class ApproveKnowledgeRequest(BaseModel):
    tenant_id: str
    change_ids: list[UUID] = Field(default_factory=list)
    approve_all_proposed: bool = False
    actor: str | None = None
    note: str | None = None
