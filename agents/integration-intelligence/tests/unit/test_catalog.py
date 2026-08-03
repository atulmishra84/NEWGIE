from integration_intelligence.domain.catalog import platform_catalog
from gie_contracts.integration import PlatformId

def test_catalog_covers_required_platforms():
    ids = {p.platform_id for p in platform_catalog()}
    required = {
        PlatformId.CURSOR, PlatformId.VS_CODE, PlatformId.JETBRAINS, PlatformId.VISUAL_STUDIO,
        PlatformId.GITHUB, PlatformId.GITHUB_ACTIONS, PlatformId.AZURE_DEVOPS, PlatformId.JENKINS,
        PlatformId.GITLAB, PlatformId.BITBUCKET, PlatformId.AZURE_AI_FOUNDRY, PlatformId.LANGGRAPH,
        PlatformId.CREWAI, PlatformId.OPENAI_AGENTS_SDK, PlatformId.GOOGLE_ADK, PlatformId.SEMANTIC_KERNEL,
        PlatformId.AUTOGEN, PlatformId.MCP, PlatformId.SERVICENOW, PlatformId.ENTRA_ID, PlatformId.OKTA,
        PlatformId.SPLUNK, PlatformId.MICROSOFT_SENTINEL, PlatformId.GOOGLE_SECOPS, PlatformId.ELASTIC,
        PlatformId.HASHICORP_VAULT, PlatformId.CYBERARK, PlatformId.AZURE_KEY_VAULT,
    }
    assert required.issubset(ids)
    assert len(platform_catalog()) >= 28
