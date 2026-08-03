import json
import pytest
import pytest_asyncio
from gie_contracts.validation import ValidationInputBundle
from validation_intelligence.infrastructure.bootstrap import build_container
from validation_intelligence.settings import Settings

@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False)

@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)

@pytest.fixture
def sample_bundle():
    openai = {
        "object": "guardrails.policy",
        "name": "agent-checkout-bot",
        "version": "1.0.0",
        "steps": [
            {"type": "input_filters", "filters": ["jailbreak", "pii"]},
            {"type": "tool_restrictions", "mode": "allowlist"},
        ],
        "controls": ["gr-prompt-firewall", "gr-pii-presidio", "gr-tool-allowlist"],
        "rules": {
            "block_prompt_injection": True,
            "redact_pii": True,
            "tool_allowlist": True,
            "require_human_approval": True,
            "rate_limit": True,
        },
    }
    rego = """package gie.guardrails

default allow = false

allow {
  input.action == "invoke"
  not deny
}

deny {
  input.prompt_injection_score > 0.7
}
"""
    return ValidationInputBundle(
        tenant_id="acme",
        agent_id="agent-checkout-bot",
        policy_package={
            "named_artifacts": {
                "openai-policy.json": json.dumps(openai),
                "opa.rego": rego,
                "guardrails.json": json.dumps({"apiVersion": "gie.ai/v1", "kind": "GuardrailsPolicy", "metadata": {"name": "agent"}, "spec": {"rules": openai["rules"], "controls": openai["controls"]}}),
            }
        },
        context={"ai": {"frameworks": [{"name": "langgraph"}], "models": [{"name": "gpt-4o"}]}, "deployment": {"exposure": "public"}},
        compliance={"compliance_score": 0.55, "gaps": [{"control_id": "gdpr-art32", "severity": "high"}]},
        runtime={"exposure": "public", "allowed_tools": ["search"]},
        frameworks=["langgraph", "openai"],
        models=[{"name": "gpt-4o"}],
    )
