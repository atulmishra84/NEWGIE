import pytest
import pytest_asyncio
from gie_contracts.learning import LearningInputBundle
from learning_intelligence.infrastructure.bootstrap import build_container
from learning_intelligence.settings import Settings

@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False, allow_auto_publish=False)

@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)

@pytest.fixture
def sample_bundle():
    return LearningInputBundle(
        tenant_id="acme",
        agent_id="agent-checkout-bot",
        current_recommendations=[
            {
                "recommendation_id": "rec-prompt-injection-abc",
                "title": "Deploy prompt-injection defenses",
                "reason": "High prompt-injection exposure",
                "priority": "medium",
                "category": "security",
                "confidence": {"score": 0.7},
                "related_guardrails": ["gr-prompt-firewall"],
            }
        ],
        false_positives=[
            {
                "title": "Benign finance query blocked",
                "recommendation_id": "rec-prompt-injection-abc",
                "severity": "medium",
                "signals": {"block_rate": 0.4, "sentiment": "negative"},
            }
        ],
        false_negatives=[
            {
                "title": "Missed jailbreak variant",
                "recommendation_id": "rec-prompt-injection-abc",
                "severity": "high",
                "signals": {"pattern": "ignore-previous-instructions-v2"},
            }
        ],
        security_incidents=[{"title": "Prompt injection incident", "severity": "critical", "recommendation_id": "rec-prompt-injection-abc"}],
        threat_intelligence=[{"title": "ATLAS new technique T1543", "severity": "high", "signals": {"technique_id": "T1543", "atlas_id": "AML.T0051"}}],
        regulatory_updates=[{"title": "EU AI Act transparency amendment", "severity": "high", "signals": {"framework": "eu_ai_act"}}],
        policy_changes=[{"title": "opa.rego updated in prod", "severity": "medium"}],
        model_changes=[{"title": "Switched to gpt-4.1", "severity": "medium"}],
        runtime_telemetry=[{"title": "edge block metrics", "signals": {"block_rate": 0.32}}],
        user_feedback=[{"title": "Too noisy", "signals": {"sentiment": "negative", "rating": "2"}}],
        current_policies={"version": "1.1.0"},
        knowledge_snapshot={"policy_version": "1.0.0", "policy_fingerprint": "abc"},
        auto_propose_knowledge=True,
        publish_without_approval=False,
    )
