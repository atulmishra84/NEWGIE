"""Full+GIE fleet contracts — agents, intents, runs, risk, policy."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class AgentLane(str, Enum):
    ORCHESTRATION = "orchestration"
    DELIVERY = "delivery"
    SECURITY = "security"
    RELEASE_OPS = "release_ops"
    PLATFORM = "platform"


class AgentId(str, Enum):
    CHIEF_ORCHESTRATOR = "chief-orchestrator"
    PRODUCT_MANAGER = "product-manager"
    UX_DESIGNER = "ux-designer"
    SENIOR_DEVELOPER = "senior-developer"
    FRONTEND_SPECIALIST = "frontend-specialist"
    BACKEND_SPECIALIST = "backend-specialist"
    SECURITY_ENGINEER = "security-engineer"
    VULNERABILITY_ENGINEER = "vulnerability-engineer"
    SECURITY_TEST_ENGINEER = "security-test-engineer"
    COMPLIANCE_OFFICER = "compliance-officer"
    QA_ENGINEER = "qa-engineer"
    RELEASE_MANAGER = "release-manager"
    DEVOPS = "devops"
    SRE_OBSERVABILITY = "sre-observability"
    TECH_WRITER = "tech-writer"
    CONTEXT_INTELLIGENCE = "context-intelligence"
    RISK_ASSESSMENT = "risk-assessment"
    POLICY_ENGINE = "policy-engine"


FLEET_AGENT_META: dict[AgentId, tuple[AgentLane, str]] = {
    AgentId.CHIEF_ORCHESTRATOR: (AgentLane.ORCHESTRATION, "Chief Orchestrator"),
    AgentId.PRODUCT_MANAGER: (AgentLane.DELIVERY, "Product Manager"),
    AgentId.UX_DESIGNER: (AgentLane.DELIVERY, "UX Designer"),
    AgentId.SENIOR_DEVELOPER: (AgentLane.DELIVERY, "Senior Developer"),
    AgentId.FRONTEND_SPECIALIST: (AgentLane.DELIVERY, "Frontend Specialist"),
    AgentId.BACKEND_SPECIALIST: (AgentLane.DELIVERY, "Backend Specialist"),
    AgentId.SECURITY_ENGINEER: (AgentLane.SECURITY, "Security Engineer (AppSec)"),
    AgentId.VULNERABILITY_ENGINEER: (AgentLane.SECURITY, "Vulnerability Engineer"),
    AgentId.SECURITY_TEST_ENGINEER: (AgentLane.SECURITY, "Security Test Engineer"),
    AgentId.COMPLIANCE_OFFICER: (AgentLane.SECURITY, "Compliance Officer"),
    AgentId.QA_ENGINEER: (AgentLane.RELEASE_OPS, "QA Engineer"),
    AgentId.RELEASE_MANAGER: (AgentLane.RELEASE_OPS, "Release Manager"),
    AgentId.DEVOPS: (AgentLane.RELEASE_OPS, "DevOps"),
    AgentId.SRE_OBSERVABILITY: (AgentLane.RELEASE_OPS, "SRE / Observability"),
    AgentId.TECH_WRITER: (AgentLane.RELEASE_OPS, "Tech Writer"),
    AgentId.CONTEXT_INTELLIGENCE: (AgentLane.PLATFORM, "Context Intelligence"),
    AgentId.RISK_ASSESSMENT: (AgentLane.PLATFORM, "Risk Assessment"),
    AgentId.POLICY_ENGINE: (AgentLane.PLATFORM, "Policy Engine"),
}

# 16-agent production fleet (orchestrator is the front door; counted in registry)
FULL_GIE_AGENT_IDS: list[AgentId] = [
    AgentId.CHIEF_ORCHESTRATOR,
    AgentId.PRODUCT_MANAGER,
    AgentId.UX_DESIGNER,
    AgentId.SENIOR_DEVELOPER,
    AgentId.FRONTEND_SPECIALIST,
    AgentId.BACKEND_SPECIALIST,
    AgentId.SECURITY_ENGINEER,
    AgentId.VULNERABILITY_ENGINEER,
    AgentId.SECURITY_TEST_ENGINEER,
    AgentId.COMPLIANCE_OFFICER,
    AgentId.QA_ENGINEER,
    AgentId.RELEASE_MANAGER,
    AgentId.DEVOPS,
    AgentId.SRE_OBSERVABILITY,
    AgentId.TECH_WRITER,
    AgentId.CONTEXT_INTELLIGENCE,
    AgentId.RISK_ASSESSMENT,
    AgentId.POLICY_ENGINE,
]


class Channel(str, Enum):
    TEXT = "text"
    VOICE = "voice"


class IntentType(str, Enum):
    STATUS = "status"
    GOLDEN_RUN = "golden_run"
    CHANGE_REQUEST = "change_request"
    PROD_APPROVE = "prod_approve"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    AWAITING_HUMAN = "awaiting_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class AgentHeartbeat(BaseModel):
    agent_id: AgentId
    lane: AgentLane
    display_name: str
    healthy: bool = True
    last_seen: datetime = Field(default_factory=_utcnow)
    version: str = "1.0.0"


class CommandRequest(BaseModel):
    text: str | None = None
    channel: Channel = Channel.TEXT
    transcript: str | None = None
    require_prod_confirm: bool = False
    prod_confirm_phrase: str | None = None
    inject_critical_finding: bool = False
    force_policy_deny: bool = False
    tenant_id: str = "default"
    correlation_id: str | None = None


class NormalizedIntent(BaseModel):
    intent: IntentType
    text: str
    channel: Channel
    confidence: float = 1.0
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    prod_confirmed: bool = False


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: _id("find"))
    source_agent: AgentId
    severity: Severity
    title: str
    detail: str = ""
    blocking: bool = False


class AgentStepResult(BaseModel):
    agent_id: AgentId
    ok: bool = True
    summary: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None


class RiskReport(BaseModel):
    risk_id: str = Field(default_factory=lambda: _id("risk"))
    score: float = Field(ge=0.0, le=100.0)
    level: Severity = Severity.LOW
    factors: list[str] = Field(default_factory=list)
    context_model_id: str | None = None


class PolicyReport(BaseModel):
    decision: PolicyDecision
    reasons: list[str] = Field(default_factory=list)
    risk_score: float | None = None
    deny_on: list[str] = Field(default_factory=list)
    llm_enhancement: dict[str, Any] | None = None


class EvidencePackage(BaseModel):
    run_id: str
    pr_url: str | None = None
    staging_url: str | None = None
    demo_summary: str = ""
    acceptance: list[str] = Field(default_factory=list)
    reports: dict[str, Any] = Field(default_factory=dict)
    voice_transcripts: list[str] = Field(default_factory=list)
    gie_context_model_id: str | None = None
    risk: RiskReport | None = None
    policy: PolicyReport | None = None


class FleetRun(BaseModel):
    run_id: str = Field(default_factory=lambda: _id("run"))
    status: RunStatus = RunStatus.PENDING
    intent: IntentType = IntentType.UNKNOWN
    channel: Channel = Channel.TEXT
    command_text: str = ""
    tenant_id: str = "default"
    correlation_id: str = Field(default_factory=lambda: _id("corr"))
    steps: list[AgentStepResult] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    evidence: EvidencePackage | None = None
    blocked_reason: str | None = None
    human_approval_required: bool = False
    human_approved: bool = False
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()


class GoNoGoReport(BaseModel):
    ready_for_prod_approve: bool
    staging_live: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    failed_checks: list[str] = Field(default_factory=list)
    demo_url: str | None = None
    evidence_run_id: str | None = None
    summary: str = ""
