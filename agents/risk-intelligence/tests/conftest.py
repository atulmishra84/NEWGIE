import pytest
import pytest_asyncio
from gie_contracts.risk import RiskInputBundle
from risk_intelligence.infrastructure.bootstrap import build_container
from risk_intelligence.settings import Settings

@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False)

@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)

@pytest.fixture
def sample_bundle():
    return RiskInputBundle(
        tenant_id="acme",
        agent_id="agent-checkout-bot",
        context_model={
            "ai": {"frameworks": [{"name": "langgraph"}, {"name": "openai"}], "autonomous_capabilities": ["tool_use"]},
            "interfaces": {"tools": [{"name": "search"}, {"name": "shell"}], "mcp_servers": [{"name": "fs"}]},
            "data": {"secret_findings": [{"kind": "api_key"}]},
            "business": {"criticality": "critical"},
        },
        knowledge_graph={"hits": [{"node_id": "owasp-llm01"}]},
        compliance_requirements={"frameworks": ["GDPR", "SOC2", "EU AI Act"]},
        identity_metadata={"providers": []},
        runtime_configuration={"exposure": "public"},
        ai_models=[{"name": "gpt-4o"}],
        prompt_analysis={"injection_likelihood": 0.7},
        tool_permissions={"allowed": [{"name": "shell"}, {"name": "search"}]},
        agent_capabilities={"autonomous": True, "multi_agent": True},
    )
