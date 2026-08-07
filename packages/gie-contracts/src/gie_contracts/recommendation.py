"""Recommendation Intelligence contracts — gie.recommendation.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


RECOMMENDATION_SCHEMA = "gie.recommendation.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationCategory(StrEnum):
    SECURITY = "security"
    PRIVACY = "privacy"
    COMPLIANCE = "compliance"
    IDENTITY = "identity"
    RUNTIME = "runtime"
    OPERATIONS = "operations"


class Audience(StrEnum):
    EXECUTIVE = "executive"
    DEVELOPER = "developer"
    SECURITY = "security"
    PLATFORM = "platform"


class ImplementationCost(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImplementationEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class RecommendationStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class RecommendationItem(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    title: str
    reason: str
    business_impact: str
    risk_reduction: float = Field(ge=0.0, le=1.0, description="Expected risk score reduction 0-1")
    implementation_cost: ImplementationCost = ImplementationCost.MEDIUM
    implementation_effort: ImplementationEffort = ImplementationEffort.MEDIUM
    estimated_time: str = "1-2 weeks"
    priority: Priority
    confidence: Confidence = Field(default_factory=Confidence)
    supporting_evidence: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    category: RecommendationCategory
    audiences: list[Audience] = Field(default_factory=list)
    related_guardrails: list[str] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)
    status: RecommendationStatus = RecommendationStatus.PROPOSED
    priority_score: float = Field(ge=0.0, le=100.0, default=0.0)


class AudienceBundle(BaseModel):
    audience: Audience
    summary: str
    items: list[RecommendationItem] = Field(default_factory=list)


class RecommendationInputBundle(BaseModel):
    tenant_id: str
    agent_id: str
    risk: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)
    identity: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)


class RecommendationReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    schema_version: str = RECOMMENDATION_SCHEMA
    tenant_id: str
    agent_id: str
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "recommendation-intelligence"
    agent_version: str = "1.0.0"
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    by_priority: dict[str, list[RecommendationItem]] = Field(default_factory=dict)
    by_audience: dict[str, AudienceBundle] = Field(default_factory=dict)
    executive_recommendations: list[RecommendationItem] = Field(default_factory=list)
    developer_recommendations: list[RecommendationItem] = Field(default_factory=list)
    security_team_recommendations: list[RecommendationItem] = Field(default_factory=list)
    platform_team_recommendations: list[RecommendationItem] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    counts: dict[str, int] = Field(default_factory=dict)
    llm_enhancement: dict[str, Any] | None = None



class RecommendationGenerateRequest(BaseModel):
    bundle: RecommendationInputBundle
    persist: bool = True


class RecommendationApproveRequest(BaseModel):
    tenant_id: str
    agent_id: str
    recommendation_ids: list[str] = Field(default_factory=list)
    approve_all: bool = False
    note: str | None = None
    actor: str | None = None
