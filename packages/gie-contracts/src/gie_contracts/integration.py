"""Integration Intelligence contracts — gie.integration.v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


INTEGRATION_SCHEMA = "gie.integration.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PlatformCategory(StrEnum):
    IDE = "ide"
    SCM = "scm"
    CI_CD = "ci_cd"
    AI_FRAMEWORK = "ai_framework"
    MCP = "mcp"
    ITSM = "itsm"
    IAM = "iam"
    SIEM = "siem"
    SECRETS = "secrets"


class PlatformId(StrEnum):
    CURSOR = "cursor"
    VS_CODE = "vs_code"
    JETBRAINS = "jetbrains"
    VISUAL_STUDIO = "visual_studio"
    GITHUB = "github"
    GITHUB_ACTIONS = "github_actions"
    AZURE_DEVOPS = "azure_devops"
    JENKINS = "jenkins"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    OPENAI_AGENTS_SDK = "openai_agents_sdk"
    GOOGLE_ADK = "google_adk"
    SEMANTIC_KERNEL = "semantic_kernel"
    AUTOGEN = "autogen"
    MCP = "mcp"
    SERVICENOW = "servicenow"
    ENTRA_ID = "entra_id"
    OKTA = "okta"
    SPLUNK = "splunk"
    MICROSOFT_SENTINEL = "microsoft_sentinel"
    GOOGLE_SECOPS = "google_secops"
    ELASTIC = "elastic"
    HASHICORP_VAULT = "hashicorp_vault"
    CYBERARK = "cyberark"
    AZURE_KEY_VAULT = "azure_key_vault"


class AuthMethod(StrEnum):
    OAUTH = "oauth"
    API_KEY = "api_key"
    JWT = "jwt"
    MTLS = "mtls"


class ConnectionStatus(StrEnum):
    PENDING = "pending"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    CIRCUIT_OPEN = "circuit_open"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str | None = None


class PlatformDescriptor(BaseModel):
    platform_id: PlatformId
    name: str
    category: PlatformCategory
    auth_methods: list[AuthMethod] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    webhook_support: bool = False
    sdk_support: bool = True
    docs_url: str | None = None


class IntegrationConnection(BaseModel):
    connection_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    platform_id: PlatformId
    name: str
    status: ConnectionStatus = ConnectionStatus.PENDING
    auth_method: AuthMethod
    config: dict[str, Any] = Field(default_factory=dict)  # non-secret config only
    scopes: list[str] = Field(default_factory=list)
    endpoint_url: str | None = None
    circuit_breaker_state: str = "closed"
    failure_count: int = 0
    last_success_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectRequest(BaseModel):
    tenant_id: str
    platform_id: PlatformId
    name: str
    auth_method: AuthMethod
    credentials: dict[str, Any] = Field(default_factory=dict)  # never persisted raw
    config: dict[str, Any] = Field(default_factory=dict)
    scopes: list[str] = Field(default_factory=list)
    endpoint_url: str | None = None
    dry_run: bool = False


class SyncRequest(BaseModel):
    connection_id: UUID | None = None
    tenant_id: str = ""
    direction: str = "outbound"  # outbound | inbound | bidirectional
    payload: dict[str, Any] = Field(default_factory=dict)
    force: bool = False


class SyncResult(BaseModel):
    sync_id: UUID = Field(default_factory=uuid4)
    connection_id: UUID
    tenant_id: str
    platform_id: PlatformId
    status: str
    records_sent: int = 0
    records_received: int = 0
    retries: int = 0
    duration_ms: int = 0
    message: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class WebhookEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    platform_id: PlatformId
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    signature_valid: bool | None = None
    received_at: datetime = Field(default_factory=utcnow)
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    last_error: str | None = None


class WebhookIngressRequest(BaseModel):
    tenant_id: str | None = None
    event_type: str = "generic"
    payload: dict[str, Any] = Field(default_factory=dict)
    signature: str | None = None


class AuthTokenRequest(BaseModel):
    tenant_id: str
    auth_method: AuthMethod
    subject: str
    scopes: list[str] = Field(default_factory=list)
    ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    claims: dict[str, Any] = Field(default_factory=dict)


class AuthTokenResponse(BaseModel):
    token_type: str
    access_token: str
    expires_in: int
    scopes: list[str] = Field(default_factory=list)
    auth_method: AuthMethod
    mtls_required: bool = False


class AuditLogEntry(BaseModel):
    audit_id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str | None = None
    platform_id: PlatformId | None = None
    outcome: str = "success"
    detail: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utcnow)


class CircuitBreakerStatus(BaseModel):
    connection_id: UUID
    platform_id: PlatformId
    state: str  # closed | open | half_open
    failure_count: int
    failure_threshold: int
    opened_at: datetime | None = None
    next_attempt_at: datetime | None = None


class IntegrationCatalogResponse(BaseModel):
    schema_version: str = INTEGRATION_SCHEMA
    platforms: list[PlatformDescriptor]
    count: int


class IntegrationHealthReport(BaseModel):
    schema_version: str = INTEGRATION_SCHEMA
    tenant_id: str
    connections_total: int = 0
    connected: int = 0
    degraded: int = 0
    circuit_open: int = 0
    webhook_deliveries_24h: int = 0
    audit_events_24h: int = 0
    confidence: Confidence = Field(default_factory=Confidence)
    reasoning_path: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
