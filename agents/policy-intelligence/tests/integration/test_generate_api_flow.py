import pytest
from gie_contracts.policy import PolicyGenerateRequest


@pytest.mark.asyncio
async def test_generate_and_explain(container, sample_bundle):
    decision = await container.generate.handle(
        PolicyGenerateRequest(bundle=sample_bundle),
        actor="test",
        correlation_id="c1",
    )
    assert decision.recommendations
    assert decision.artifacts
    assert decision.summary
    explained = await container.explain.handle(decision.decision_id)
    assert explained["decision_id"] == str(decision.decision_id)
    got = await container.decisions.get(decision.decision_id)
    assert got is not None
