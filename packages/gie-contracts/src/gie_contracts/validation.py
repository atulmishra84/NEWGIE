"""Validation Intelligence contracts — gie.validation.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


VALIDATION_SCHEMA = "gie.validation.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ValidationVerdict(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAILED = "failed"


class ApprovalStatus(StrEnum):
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    REJECTED = "rejected"
    PENDING = "pending"


class CheckCategory(StrEnum):
    SYNTAX = "syntax"
    SCHEMA = "schema"
    COMPLIANCE = "compliance"
    RUNTIME_COMPATIBILITY = "runtime_compatibility"
    POLICY_CONFLICTS = "policy_conflicts"
    DUPLICATE_RULES = "duplicate_rules"
    PERFORMANCE = "performance"
    SECURITY = "security"
    FRAMEWORK_COMPATIBILITY = "framework_compatibility"
    MODEL_COMPATIBILITY = "model_compatibility"
    SIMULATION = "simulation"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class CorrectionRecommendation(BaseModel):
    correction_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str
    description: str
    severity: str = "medium"
    category: CheckCategory
    target_path: str | None = None
    suggested_fix: dict[str, Any] | str | None = None


class ValidationFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    category: CheckCategory
    verdict: ValidationVerdict
    title: str
    detail: str
    path: str | None = None
    evidence: list[str] = Field(default_factory=list)


class CheckResult(BaseModel):
    category: CheckCategory
    verdict: ValidationVerdict
    message: str
    findings: list[ValidationFinding] = Field(default_factory=list)
    duration_ms: int = 0


class SimulationStep(BaseModel):
    step: int
    action: str
    input_summary: str
    result: str
    allowed: bool
    notes: str | None = None


class SimulationReport(BaseModel):
    scenario_id: str = Field(default_factory=lambda: uuid4().hex[:10])
    scenario_name: str
    passed: bool
    steps: list[SimulationStep] = Field(default_factory=list)
    summary: str = ""


class ValidationInputBundle(BaseModel):
    tenant_id: str
    agent_id: str | None = None
    policy_package: dict[str, Any] = Field(default_factory=dict)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    content: str | None = None
    format: str | None = None
    filename: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    runtime: dict[str, Any] = Field(default_factory=dict)
    frameworks: list[str] = Field(default_factory=list)
    models: list[dict[str, Any]] = Field(default_factory=list)
    simulation_scenarios: list[dict[str, Any]] = Field(default_factory=list)


class ValidationReport(BaseModel):
    validation_id: UUID = Field(default_factory=uuid4)
    schema_version: str = VALIDATION_SCHEMA
    tenant_id: str
    agent_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    agent_name: str = "validation-intelligence"
    agent_version: str = "1.0.0"
    verdict: ValidationVerdict = ValidationVerdict.PASS
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    checks: list[CheckResult] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    corrections: list[CorrectionRecommendation] = Field(default_factory=list)
    simulations: list[SimulationReport] = Field(default_factory=list)
    invalid_configurations: list[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    counts: dict[str, int] = Field(default_factory=dict)


class ValidateRequest(BaseModel):
    bundle: ValidationInputBundle
    persist: bool = True
    run_simulation: bool = True


class SimulateRequest(BaseModel):
    tenant_id: str
    agent_id: str | None = None
    policy_package: dict[str, Any] = Field(default_factory=dict)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    content: str | None = None
    runtime: dict[str, Any] = Field(default_factory=dict)
    scenarios: list[dict[str, Any]] = Field(default_factory=list)
