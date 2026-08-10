import pytest
import pytest_asyncio
from gie_contracts.policy_generator import PolicyGeneratorInputBundle
from policy_generator.infrastructure.bootstrap import build_container
from policy_generator.settings import Settings


@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False)


@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)


@pytest.fixture
def sample_bundle():
    return PolicyGeneratorInputBundle(
        tenant_id="acme",
        agent_id="agent-checkout-bot",
        recommendations=[
            {
                "recommendation_id": "rec-prompt-injection-abc",
                "title": "Deploy prompt-injection defenses",
                "priority": "critical",
                "category": "security",
                "risk_reduction": 0.22,
                "related_guardrails": ["gr-prompt-firewall", "gr-input-sanitize"],
                "knowledge_refs": ["owasp-llm01"],
            },
            {
                "recommendation_id": "rec-pii-presidio-def",
                "title": "Enforce PII/PHI redaction",
                "priority": "critical",
                "category": "privacy",
                "risk_reduction": 0.2,
                "related_guardrails": ["gr-pii-presidio", "gr-output-filter"],
                "knowledge_refs": ["gdpr-art32", "hipaa-phi"],
            },
            {
                "recommendation_id": "rec-tool-allowlist-ghi",
                "title": "Constrain tools with allowlist",
                "priority": "high",
                "category": "runtime",
                "risk_reduction": 0.25,
                "related_guardrails": ["gr-tool-allowlist"],
                "knowledge_refs": ["owasp-llm08"],
            },
        ],
        risk={
            "overall_ai_risk_score": 0.7,
            "factors": [{"category": "prompt_injection", "score": 0.8}],
        },
        compliance={
            "compliance_score": 0.4,
            "applicable_frameworks": [{"framework": "gdpr"}, {"framework": "hipaa"}],
            "gaps": [{"framework": "gdpr", "control_id": "gdpr-art32"}],
        },
        context={"ai": {"frameworks": [{"name": "langgraph"}]}},
        source="recommendation-intelligence",
        policy_version="1.0.0",
    )
