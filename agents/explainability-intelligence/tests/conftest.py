import pytest
import pytest_asyncio
from gie_contracts.explainability import ExplainabilityInputBundle
from explainability_intelligence.infrastructure.bootstrap import build_container
from explainability_intelligence.settings import Settings


@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False)


@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)


@pytest.fixture
def sample_bundle():
    return ExplainabilityInputBundle(
        tenant_id="acme",
        agent_id="agent-checkout-bot",
        decision_id="rec-prompt-injection-abc",
        subject_type="recommendation",
        recommendations=[
            {
                "recommendation_id": "rec-prompt-injection-abc",
                "title": "Deploy prompt-injection defenses",
                "reason": "High prompt-injection exposure detected",
                "business_impact": "Prevents unauthorized actions and brand damage",
                "priority": "critical",
                "risk_reduction": 0.22,
                "confidence": {"score": 0.9},
                "supporting_evidence": [
                    "Signal matched: prompt_injection",
                    "Overall AI risk score=0.72",
                ],
                "related_guardrails": ["gr-prompt-firewall"],
                "knowledge_refs": ["owasp-llm01", "atlas-prompt-injection"],
            }
        ],
        risk={
            "overall_ai_risk_score": 0.72,
            "factors": [
                {"category": "prompt_injection", "score": 0.8, "severity": "critical"}
            ],
        },
        compliance={
            "compliance_score": 0.4,
            "applicable_frameworks": [{"framework": "eu_ai_act"}],
            "gaps": [{"control_id": "euai-transparency", "severity": "high"}],
        },
        knowledge={"hits": [{"node_id": "owasp-llm01"}]},
        policy_package={"source": "policy-generator"},
    )
