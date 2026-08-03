import pytest
from gie_contracts.risk import RiskCalculateRequest, RiskRecalculateRequest

@pytest.mark.asyncio
async def test_calculate_history_remediation(container, sample_bundle):
    r1 = await container.calculate.handle(RiskCalculateRequest(bundle=sample_bundle), actor="t", correlation_id="c1")
    assert r1.agent_id == "agent-checkout-bot"
    hist = await container.reports.history("acme", agent_id="agent-checkout-bot")
    assert len(hist) >= 1
    r2 = await container.recalculate.handle(
        RiskRecalculateRequest(agent_id="agent-checkout-bot", tenant_id="acme", org_risk_model={"weights": {"tool_abuse": 2.0}}),
        actor="t",
        correlation_id="c2",
    )
    assert r2.report_id != r1.report_id
    latest = await container.reports.latest_for_agent("acme", "agent-checkout-bot")
    assert latest is not None
    assert latest.remediations
