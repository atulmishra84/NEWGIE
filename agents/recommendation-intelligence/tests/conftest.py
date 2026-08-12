import pytest
import pytest_asyncio
from gie_contracts.recommendation import RecommendationInputBundle
from recommendation_intelligence.infrastructure.bootstrap import build_container
from recommendation_intelligence.settings import Settings


@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False)


@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)


@pytest.fixture
def sample_bundle():
    return RecommendationInputBundle(
        tenant_id="acme",
        agent_id="agent-checkout-bot",
        risk={
            "overall_ai_risk_score": 0.72,
            "factors": [
                {"category": "prompt_injection", "score": 0.8, "severity": "critical"},
                {"category": "privacy", "score": 0.7, "severity": "high"},
                {"category": "tool_abuse", "score": 0.75, "severity": "high"},
                {"category": "identity", "score": 0.6, "severity": "medium"},
                {"category": "runtime", "score": 0.55, "severity": "medium"},
            ],
            "remediations": [{"title": "Add tool allowlist"}],
        },
        compliance={
            "compliance_score": 0.42,
            "gaps": [
                {
                    "control_id": "hipaa-phi-min",
                    "title": "PHI minimization",
                    "severity": "critical",
                },
                {"control_id": "gdpr-art32", "severity": "high"},
            ],
            "applicable_frameworks": [
                {"framework": "hipaa"},
                {"framework": "gdpr"},
                {"framework": "eu_ai_act"},
            ],
        },
        context={
            "ai": {
                "frameworks": [{"name": "langgraph"}],
                "models": [{"name": "gpt-4o"}],
            },
            "data": {"secret_findings": [{"kind": "api_key"}], "pii_types": ["phi"]},
            "interfaces": {
                "tools": [{"name": "shell"}, {"name": "search"}],
                "mcp_servers": [{"name": "fs"}],
            },
            "deployment": {"exposure": "public"},
        },
        knowledge={
            "hits": [{"node_id": "owasp-llm01"}, {"node_id": "atlas-prompt-injection"}]
        },
        policies={"recommendations": [{"id": "gr-pii-presidio"}]},
        identity={"providers": [], "mfa": False, "weak_identity": True},
        runtime={"exposure": "public", "rate_limits": False},
    )
