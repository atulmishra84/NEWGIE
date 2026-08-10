"""Supported enterprise platform catalog."""

from __future__ import annotations
from gie_contracts.integration import (
    AuthMethod,
    PlatformCategory,
    PlatformDescriptor,
    PlatformId,
)

_CAP_COMMON = ["rest", "webhooks", "sdk", "audit"]
_CAP_CI = ["rest", "webhooks", "pipeline", "sdk", "audit"]
_CAP_AI = ["rest", "sdk", "policy_push", "runtime_hooks", "audit"]
_CAP_SIEM = ["rest", "webhooks", "event_forward", "audit"]
_CAP_SECRETS = ["rest", "secret_resolve", "rotation_hook", "audit", "mtls"]
_CAP_IDE = ["extension", "sdk", "mcp", "local_policy", "audit"]
_CAP_IAM = ["oauth", "scim", "jwt", "audit"]


def platform_catalog() -> list[PlatformDescriptor]:
    rows: list[
        tuple[PlatformId, str, PlatformCategory, list[AuthMethod], list[str], bool]
    ] = [
        (
            PlatformId.CURSOR,
            "Cursor",
            PlatformCategory.IDE,
            [AuthMethod.API_KEY, AuthMethod.JWT, AuthMethod.OAUTH],
            _CAP_IDE,
            True,
        ),
        (
            PlatformId.VS_CODE,
            "VS Code",
            PlatformCategory.IDE,
            [AuthMethod.API_KEY, AuthMethod.JWT, AuthMethod.OAUTH],
            _CAP_IDE,
            True,
        ),
        (
            PlatformId.JETBRAINS,
            "JetBrains",
            PlatformCategory.IDE,
            [AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_IDE,
            False,
        ),
        (
            PlatformId.VISUAL_STUDIO,
            "Visual Studio",
            PlatformCategory.IDE,
            [AuthMethod.API_KEY, AuthMethod.OAUTH],
            _CAP_IDE,
            False,
        ),
        (
            PlatformId.GITHUB,
            "GitHub",
            PlatformCategory.SCM,
            [AuthMethod.OAUTH, AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_CI,
            True,
        ),
        (
            PlatformId.GITHUB_ACTIONS,
            "GitHub Actions",
            PlatformCategory.CI_CD,
            [AuthMethod.JWT, AuthMethod.API_KEY],
            _CAP_CI,
            True,
        ),
        (
            PlatformId.AZURE_DEVOPS,
            "Azure DevOps",
            PlatformCategory.CI_CD,
            [AuthMethod.OAUTH, AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_CI,
            True,
        ),
        (
            PlatformId.JENKINS,
            "Jenkins",
            PlatformCategory.CI_CD,
            [AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_CI,
            True,
        ),
        (
            PlatformId.GITLAB,
            "GitLab",
            PlatformCategory.SCM,
            [AuthMethod.OAUTH, AuthMethod.API_KEY],
            _CAP_CI,
            True,
        ),
        (
            PlatformId.BITBUCKET,
            "Bitbucket",
            PlatformCategory.SCM,
            [AuthMethod.OAUTH, AuthMethod.API_KEY],
            _CAP_CI,
            True,
        ),
        (
            PlatformId.AZURE_AI_FOUNDRY,
            "Azure AI Foundry",
            PlatformCategory.AI_FRAMEWORK,
            [AuthMethod.OAUTH, AuthMethod.API_KEY, AuthMethod.MTLS],
            _CAP_AI,
            True,
        ),
        (
            PlatformId.LANGGRAPH,
            "LangGraph",
            PlatformCategory.AI_FRAMEWORK,
            [AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_AI,
            False,
        ),
        (
            PlatformId.CREWAI,
            "CrewAI",
            PlatformCategory.AI_FRAMEWORK,
            [AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_AI,
            False,
        ),
        (
            PlatformId.OPENAI_AGENTS_SDK,
            "OpenAI Agents SDK",
            PlatformCategory.AI_FRAMEWORK,
            [AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_AI,
            False,
        ),
        (
            PlatformId.GOOGLE_ADK,
            "Google ADK",
            PlatformCategory.AI_FRAMEWORK,
            [AuthMethod.OAUTH, AuthMethod.API_KEY],
            _CAP_AI,
            False,
        ),
        (
            PlatformId.SEMANTIC_KERNEL,
            "Semantic Kernel",
            PlatformCategory.AI_FRAMEWORK,
            [AuthMethod.API_KEY, AuthMethod.OAUTH],
            _CAP_AI,
            False,
        ),
        (
            PlatformId.AUTOGEN,
            "AutoGen",
            PlatformCategory.AI_FRAMEWORK,
            [AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_AI,
            False,
        ),
        (
            PlatformId.MCP,
            "MCP",
            PlatformCategory.MCP,
            [AuthMethod.API_KEY, AuthMethod.JWT, AuthMethod.MTLS],
            ["mcp_server", "tools", "resources", "audit"],
            False,
        ),
        (
            PlatformId.SERVICENOW,
            "ServiceNow",
            PlatformCategory.ITSM,
            [AuthMethod.OAUTH, AuthMethod.API_KEY],
            _CAP_COMMON + ["incident_create"],
            True,
        ),
        (
            PlatformId.ENTRA_ID,
            "Entra ID",
            PlatformCategory.IAM,
            [AuthMethod.OAUTH, AuthMethod.JWT, AuthMethod.MTLS],
            _CAP_IAM,
            True,
        ),
        (
            PlatformId.OKTA,
            "Okta",
            PlatformCategory.IAM,
            [AuthMethod.OAUTH, AuthMethod.JWT, AuthMethod.API_KEY],
            _CAP_IAM,
            True,
        ),
        (
            PlatformId.SPLUNK,
            "Splunk",
            PlatformCategory.SIEM,
            [AuthMethod.API_KEY, AuthMethod.JWT, AuthMethod.MTLS],
            _CAP_SIEM,
            True,
        ),
        (
            PlatformId.MICROSOFT_SENTINEL,
            "Microsoft Sentinel",
            PlatformCategory.SIEM,
            [AuthMethod.OAUTH, AuthMethod.MTLS],
            _CAP_SIEM,
            True,
        ),
        (
            PlatformId.GOOGLE_SECOPS,
            "Google SecOps",
            PlatformCategory.SIEM,
            [AuthMethod.OAUTH, AuthMethod.API_KEY],
            _CAP_SIEM,
            True,
        ),
        (
            PlatformId.ELASTIC,
            "Elastic",
            PlatformCategory.SIEM,
            [AuthMethod.API_KEY, AuthMethod.JWT],
            _CAP_SIEM,
            True,
        ),
        (
            PlatformId.HASHICORP_VAULT,
            "HashiCorp Vault",
            PlatformCategory.SECRETS,
            [AuthMethod.JWT, AuthMethod.API_KEY, AuthMethod.MTLS],
            _CAP_SECRETS,
            False,
        ),
        (
            PlatformId.CYBERARK,
            "CyberArk",
            PlatformCategory.SECRETS,
            [AuthMethod.OAUTH, AuthMethod.API_KEY, AuthMethod.MTLS],
            _CAP_SECRETS,
            False,
        ),
        (
            PlatformId.AZURE_KEY_VAULT,
            "Azure Key Vault",
            PlatformCategory.SECRETS,
            [AuthMethod.OAUTH, AuthMethod.MTLS],
            _CAP_SECRETS,
            False,
        ),
    ]
    return [
        PlatformDescriptor(
            platform_id=pid,
            name=name,
            category=cat,
            auth_methods=auths,
            capabilities=caps,
            webhook_support=wh,
            docs_url=f"https://docs.gie.local/integrations/{pid.value}",
        )
        for pid, name, cat, auths, caps, wh in rows
    ]


def get_platform(platform_id: PlatformId) -> PlatformDescriptor | None:
    for p in platform_catalog():
        if p.platform_id == platform_id:
            return p
    return None
