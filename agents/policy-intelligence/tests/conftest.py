import pytest
import pytest_asyncio

from policy_intelligence.infrastructure.bootstrap import build_container
from policy_intelligence.settings import Settings


@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False)


@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)


@pytest.fixture
def sample_bundle():
    from gie_contracts.policy import OutputFormat, PolicyInputBundle, PolicyTarget

    return PolicyInputBundle(
        tenant_id="acme",
        context={
            "ai": {
                "frameworks": [{"name": "langgraph"}, {"name": "openai"}],
                "autonomous_capabilities": ["tool_use"],
            },
            "interfaces": {
                "tools": [{"name": "search"}, {"name": "shell"}],
                "mcp_servers": [{"name": "fs"}],
            },
        },
        risk={"overall_score": 0.82, "findings": [{"id": "R1", "title": "Prompt injection"}]},
        compliance={"frameworks": ["SOC2", "GDPR", "EU AI Act"], "controls": ["gdpr-art32"]},
        knowledge={"hits": [{"node_id": "owasp-llm01", "title": "Prompt Injection"}]},
        identity={"providers": ["entra_id"], "auth_schemes": ["oauth2"]},
        business={"criticality": "critical", "industry": "healthcare"},
        targets=[
            PolicyTarget.OPENAI,
            PolicyTarget.LANGGRAPH,
            PolicyTarget.OPA_REGO,
            PolicyTarget.PRESIDIO,
        ],
        formats=list(OutputFormat),
    )
